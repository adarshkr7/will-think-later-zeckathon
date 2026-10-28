"""Phase 2 acceptance and collection coverage, separate from primary training."""

from __future__ import annotations

import math

import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.financials import financial_table
from prahari.data.manual import read_manual
from prahari.eval.coverage import coverage_parity
from prahari.eval.market_coverage import market_coverage
from prahari.data.bhavcopy import market_as_of


def panel_acceptance(events: pd.DataFrame, peers: pd.DataFrame, market: pd.DataFrame,
                     accounting: pd.DataFrame, settings: dict, financials: pd.DataFrame | None = None) -> pd.DataFrame:
    """No event/peer duplication or incomplete market checks can pass the gate."""
    events = events.loc[events.needs_verification.eq(0)]
    peers = peers.loc[peers.needs_verification.eq(0)]
    case_ids, peer_ids = set(events.entity_id), set(peers.entity_id)
    metadata = events.reindex(columns=["sector", "is_financial", "nse_symbol", "bse_code", "isin"])
    metadata_ok = bool(case_ids) and metadata[["sector", "is_financial"]].notna().all().all() and metadata[["nse_symbol", "bse_code", "isin"]].notna().any(axis=1).all()
    adequate_matches = all(peers.loc[peers.matched_to.eq(entity)].entity_id.nunique() >= settings["peers_per_case"]
                           for entity in case_ids) and bool(case_ids)
    stressed = peers.drop_duplicates("entity_id").is_stressed_survivor.eq(1).sum()
    market_ok = (not market.empty and {"entity_id", "complete"}.issubset(market)
                 and (case_ids | peer_ids).issubset(set(market.loc[market.complete.eq(1), "entity_id"])))
    identity_ok = (not accounting.empty and accounting.identity_status.eq("pass").any()
                   and not accounting.identity_status.isin(["fail", "invalid_assets"]).any())
    financial_ok = False
    if financials is not None and not financials.empty:
        financial_ok = bool(case_ids) and financials.complete.eq(1).all() and (case_ids | peer_ids).issubset(set(financials.entity_id))
    checks = [("verified_events", len(case_ids), settings["minimum_cases"], len(case_ids) >= settings["minimum_cases"]),
              ("case_identity_and_classification", int(metadata_ok), 1, metadata_ok),
              ("unique_verified_peers", len(peer_ids), settings["minimum_unique_peers"], len(peer_ids) >= settings["minimum_unique_peers"]),
              ("disjoint_cases_peers", len(case_ids & peer_ids), 0, not case_ids.intersection(peer_ids)),
              ("peers_per_case", int(adequate_matches), 1, adequate_matches),
              ("stressed_survivors", int(stressed), math.ceil(len(peer_ids) * settings["stressed_fraction"]),
               bool(peer_ids) and stressed >= math.ceil(len(peer_ids) * settings["stressed_fraction"])),
              ("panel_market_coverage", int(market_ok), 1, market_ok),
              ("financial_year_coverage", int(financial_ok), 1, financial_ok),
              ("accounting_identities", int(identity_ok), 1, identity_ok)]
    return pd.DataFrame([{"check": name, "observed": value, "required": required, "passed": int(passed),
                          "is_synthetic": int(events.is_synthetic.eq(1).any() or peers.is_synthetic.eq(1).any())}
                         for name, value, required, passed in checks])


def audit_coverage(config: Config, t: str) -> pd.DataFrame:
    events, peers = read_manual(config, "events"), read_manual(config, "peers")
    events, peers = events.loc[events.needs_verification.eq(0)], peers.loc[peers.needs_verification.eq(0)]
    cohorts = pd.concat([events[["entity_id", "is_synthetic"]].assign(role="case"),
                         peers[["entity_id", "is_synthetic"]].drop_duplicates("entity_id").assign(role="peer")])
    snapshot = as_of(financial_table(config), t)
    snapshot = snapshot.loc[snapshot.basis.eq("standalone")].sort_values("period_end")
    snapshot = snapshot.drop_duplicates(["entity_id", "field"], keep="last")
    fields = config.section("manual_config")["tables"]["annual_financials"]["numeric"]
    if snapshot.empty:
        wide = pd.DataFrame(columns=["entity_id", *fields, "is_synthetic"])
    else:
        wide = snapshot.pivot(index="entity_id", columns="field", values="value").reset_index()
        wide["is_synthetic"] = 0
        for field in fields:
            if field not in wide:
                wide[field] = float("nan")
    return coverage_parity(wide, cohorts, fields, config.section("india_config")["coverage"])


def audit_market(config: Config) -> pd.DataFrame:
    settings = config.section("india_config")["panel"]
    events, peers = read_manual(config, "events"), read_manual(config, "peers")
    events = events.loc[events.needs_verification.eq(0)]
    peers = peers.loc[peers.needs_verification.eq(0)]
    rows = []
    for case in events.to_dict(orient="records"):
        end = pd.to_datetime(case["event_date"], utc=True)
        start = end - pd.DateOffset(years=settings["history_years"])
        for entity in {case["entity_id"], *peers.loc[peers.matched_to.eq(case["entity_id"]), "entity_id"]}:
            rows.append({"entity_id": entity, "start": start, "end": end, "is_synthetic": 0})
    windows = pd.DataFrame(rows, columns=["entity_id", "start", "end", "is_synthetic"])
    if windows.empty:
        return market_coverage(windows, pd.DataFrame(), pd.DataFrame())
    windows = windows.groupby("entity_id", as_index=False).agg(start=("start", "min"), end=("end", "max"), is_synthetic=("is_synthetic", "max"))
    now = pd.Timestamp.now(tz="UTC")
    calendar = as_of(read_manual(config, "trading_calendar"), now)
    # NSE panel calendar; BSE calendar evidence is retained separately when supplied.
    calendar = calendar.loc[calendar.entity_id.str.casefold().eq("nse")]
    return market_coverage(windows, market_as_of(config, now), calendar)


def audit_financial_histories(config: Config) -> pd.DataFrame:
    settings = config.section("india_config")
    events, peers = read_manual(config, "events"), read_manual(config, "peers")
    events = events.loc[events.needs_verification.eq(0)]
    peers = peers.loc[peers.needs_verification.eq(0)]
    table = financial_table(config)
    rows = []
    for case in events.to_dict(orient="records"):
        cutoff = pd.to_datetime(case["event_date"], utc=True)
        known = as_of(table, cutoff)
        first_period = cutoff - pd.DateOffset(years=settings["panel"]["collection_years_before"])
        known = known.loc[known.period_end.ge(first_period)]
        for entity in {case["entity_id"], *peers.loc[peers.matched_to.eq(case["entity_id"]), "entity_id"]}:
            if entity == case["entity_id"]:
                financial = case["is_financial"]
            else:
                financial = peers.loc[peers.entity_id.eq(entity), "is_financial"].iloc[0]
            classification_known = pd.notna(financial)
            required = set(settings["financials"]["required_financial" if classification_known and financial else "required_nonfinancial"])
            available = known.loc[known.entity_id.eq(entity) & known.basis.eq("standalone")]
            periods = available.groupby("period_end").field.agg(set)
            complete_years = sum(required.issubset(fields) for fields in periods) if classification_known else 0
            rows.append({"entity_id": entity, "matched_to": case["entity_id"], "cutoff": cutoff,
                         "complete_years": complete_years, "required_years": settings["panel"]["minimum_financial_years"],
                         "complete": int(complete_years >= settings["panel"]["minimum_financial_years"]),
                         "needs_verification": int(complete_years < settings["panel"]["minimum_financial_years"]),
                         "missing_reason": "classification_unknown" if not classification_known else (
                             "" if complete_years >= settings["panel"]["minimum_financial_years"] else "insufficient_complete_financial_years"),
                         "is_synthetic": int(case["is_synthetic"] or known.is_synthetic.eq(1).any())})
    return pd.DataFrame(rows, columns=["entity_id", "matched_to", "cutoff", "complete_years", "required_years", "complete", "needs_verification", "missing_reason", "is_synthetic"])
