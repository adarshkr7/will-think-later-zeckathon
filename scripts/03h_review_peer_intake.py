"""Audit received peer claims without promoting them into the verified panel."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.bhavcopy import archive_url, parse_bhavcopy
from prahari.data.downloads import CachedDownloader
from prahari.data.financials import financials_as_of
from prahari.data.firewall import write_real_table
from prahari.data.manual import read_manual
from prahari.data.uci import sha256_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    settings = config.section("peer_intake_config")
    schemas = config.section("manual_config")["tables"]
    policy = config.section("india_config")["panel"]
    market = config.section("india_config")["market"]
    events = read_manual(config, "events").set_index("entity_id")
    reviewed = financials_as_of(config, pd.Timestamp.now(tz="UTC"))
    discoveries = pd.read_csv(config.path("peer_discovery_candidates"))
    frames, origins = {}, {}
    client = CachedDownloader(config)
    try:
        for table, pattern in settings["patterns"].items():
            frames[table] = []
            for path in sorted((config.root / settings["directory"]).glob(pattern)):
                digest = sha256_file(path)
                raw = client.register_manual("manual", path.resolve().as_uri(),
                                             path.stem + "_received_" + digest[:16] + path.suffix, path)
                frame = pd.read_csv(raw, dtype=str)
                frame["_file"], frame["_raw"] = path.name, raw.relative_to(config.root).as_posix()
                frame["_batch"] = path.stem.removeprefix(table + "_").removeprefix("batch_")
                frames[table].append(frame)
                origins[path.name] = {"raw": raw.relative_to(config.root).as_posix(), "sha256": digest}
            frames[table] = pd.concat(frames[table], ignore_index=True) if frames[table] else pd.DataFrame()
        if any(frame.empty for frame in frames.values()):
            raise ValueError("All three peer-claim tables are required for intake review")
        output, quote_cache = [], {}
        for table, frame in frames.items():
            for filename, batch in frame.groupby("_file", sort=False):
                missing = sorted(set(schemas[table]["columns"]) - set(frame))
                for position, row in enumerate(batch.to_dict(orient="records"), 2):
                    issues = ["missing_schema_columns:" + ",".join(missing)] if missing else []
                    related = frames["peer_survival"]
                    related = related.loc[related._batch.eq(row["_batch"]) & related.entity_id.eq(row["entity_id"])]
                    case = related.matched_to.iloc[0] if related.matched_to.nunique() == 1 else None
                    cutoff, observed_id, quote_source, reference = pd.NaT, "", "", ""
                    if case in events.index:
                        event = pd.to_datetime(events.loc[case, "event_date"], utc=True)
                        cutoff = event - pd.DateOffset(months=3 * policy["match_lag_quarters"])
                    else:
                        issues.append("case_mapping_unknown_or_ambiguous")
                    if "screener.in" in str(row.get("source_url", "")):
                        issues.append("current_third_party_page_requires_original_disclosure")
                    if table == "entities":
                        issues.append("historical_classification_requires_original_evidence")
                        if pd.notna(cutoff) and pd.to_datetime(row["public_date"], utc=True) >= cutoff:
                            issues.append("metadata_not_public_before_matching_cutoff")
                        if pd.notna(cutoff):
                            if cutoff not in quote_cache:
                                quote_tables = []
                                for day in pd.date_range(cutoff - pd.Timedelta(days=settings["identity_lookback_days"]), cutoff):
                                    url, name = archive_url(day, market)
                                    if not (config.path("raw") / "nse" / name).is_file():
                                        continue
                                    raw = client.fetch("nse", url, name, offline=True)
                                    parsed = parse_bhavcopy(raw.read_bytes(), url, market)
                                    if not parsed.period_end.eq(day).all():
                                        raise ValueError("Original identity archive date mismatch")
                                    quote_tables.append(parsed)
                                quote_cache[cutoff] = as_of(pd.concat(quote_tables, ignore_index=True), cutoff) if quote_tables else pd.DataFrame()
                            quotes = quote_cache[cutoff]
                            quotes = quotes.loc[quotes.symbol.eq(row["symbols"])] if not quotes.empty else quotes
                            if quotes.empty:
                                issues.append("matching_quote_identity_not_verified")
                            else:
                                latest = quotes.sort_values(["period_end", "series"]).iloc[-1]
                                observed_id, quote_source = latest.entity_id, latest.source_url
                                if observed_id != row["entity_id"]:
                                    issues.append("historical_security_id_differs_requires_source_resolution")
                    elif table == "peer_survival":
                        issues.append("affirmative_full_window_survival_evidence_missing")
                        if pd.notna(cutoff):
                            if pd.to_datetime(row["nondefault_start"], utc=True) > cutoff:
                                issues.append("claimed_survival_starts_after_required_window")
                            through = event + pd.DateOffset(months=3 * policy["survival_quarters"])
                            if pd.to_datetime(row["nondefault_through"], utc=True) < through:
                                issues.append("claimed_survival_ends_before_required_window")
                    else:
                        issues.extend(["source_units_and_accounting_basis_missing", "complete_peer_history_missing"])
                        end = pd.to_datetime(row["period_end"], utc=True)
                        if pd.notna(cutoff) and end >= cutoff:
                            issues.append("financial_period_ends_after_matching_cutoff")
                        if pd.notna(cutoff) and pd.to_datetime(row["public_date"], utc=True) >= cutoff:
                            issues.append("financials_not_public_before_matching_cutoff")
                        entity = row["entity_id"]
                        meta = frames["entities"]
                        symbol_rows = meta.loc[meta._batch.eq(row["_batch"]) & meta.entity_id.eq(entity)]
                        if not symbol_rows.empty:
                            leads = discoveries.loc[discoveries.symbol.eq(symbol_rows.symbols.iloc[0])].entity_id.unique()
                            if len(leads) == 1:
                                entity = leads[0]
                        candidates = reviewed.loc[reviewed.entity_id.eq(entity) & reviewed.period_end.eq(end)
                                                  & reviewed.basis.eq("standalone")]
                        compared = []
                        for field in ("total_assets", "total_liabilities"):
                            cell = candidates.loc[candidates.field.eq(field)]
                            if cell.empty:
                                continue
                            cell = cell.sort_values("public_date").iloc[-1]
                            claimed = float(row[field])
                            multiplier = config.section("india_config")["financials"]["unit_multipliers"][settings["claimed_comparison_unit"]]
                            value = float(cell.value) / multiplier
                            compared.append(field + (":rounded_value_agrees" if round(value) == claimed else ":differs_from_reviewed_original"))
                            reference += str(cell.source_doc) + "#page=" + str(int(cell.source_page)) + ";"
                        issues.extend(compared or ["original_statement_comparison_pending"])
                    output.append({"table": table, "received_file": filename, "source_row": position,
                                   "claimed_entity_id": row["entity_id"], "matched_to": case,
                                   "matching_cutoff": cutoff, "observed_historical_security_id": observed_id,
                                   "identity_source": quote_source, "reviewed_statement_source": reference,
                                   "raw_intake": row["_raw"], "sha256": origins[filename]["sha256"],
                                   "issues": ";".join(issues), "approved_for_model": 0,
                                   "needs_verification": 1, "is_synthetic": 0})
        write_real_table(pd.DataFrame(output), config.path("peer_intake_review"))
        logging.info("Reviewed received claim rows=%s approved=0; original files and canonical tables unchanged", len(output))
    finally:
        client.close()


if __name__ == "__main__":
    main()
