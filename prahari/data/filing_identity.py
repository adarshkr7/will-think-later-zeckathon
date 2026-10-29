"""Audit filing-index claims and verify security identities in original archives."""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import unquote, urlparse

import pandas as pd

from prahari.config import Config
from prahari.data.downloads import CachedDownloader
from prahari.data.firewall import assert_real, write_real_table
from prahari.data.manual import read_manual
from prahari.data.quality import validate_table
from prahari.data.uci import sha256_file
from prahari.data.bhavcopy import market_as_of, parse_bhavcopy

LOG = logging.getLogger(__name__)


def filing_identity(row: dict, allowed: set[str], source_url: str, settings: dict) -> dict | None:
    """Retain a filing-index claim and latest stated dissemination time.

    Index identifiers can be stale or retrospectively normalized. This claim
    remains unverified until corroborated against an original security source.
    Every supplied timestamp must parse; missing timing never becomes a lag.
    """
    entity = str(row.get("isin") or "").strip()
    symbol = str(row.get("symbol") or "").strip()
    if entity not in allowed or not symbol:
        return None
    # Current exchange indexes can normalize renamed tickers retrospectively.
    # Require agreement with the original resource's sequence-qualified name.
    detail = urlparse(str(row.get("resultDetailedDataLink") or ""))
    pattern = settings["legacy_filename_pattern"].format(sequence=re.escape(str(row.get("seqNumber") or "")))
    original = re.fullmatch(pattern, unquote(detail.path.rsplit("/", 1)[-1]))
    if detail.scheme != "https" or detail.hostname != settings["legacy_host"] or original is None or original["symbol"] != symbol:
        return None
    raw_dates = [row.get(key) for key in ("exchdisstime", "broadCastDate", "filingDate")]
    dates = []
    for value in raw_dates:
        if value is None or str(value).strip() in ("", "-", "::"):
            continue
        date = pd.Timestamp(value)
        dates.append(date.tz_localize(settings["timezone"]).tz_convert("UTC") if date.tzinfo is None else date.tz_convert("UTC"))
    if not dates or not row.get("toDate") or not row.get("seqNumber"):
        return None
    period = pd.Timestamp(row["toDate"]).normalize()
    if period.tzinfo is not None:
        raise ValueError("Unexpected timezone in filing observation period")
    public = max(dates)
    if public < period.tz_localize("UTC"):
        raise ValueError("Identity filing publication precedes its stated period")
    return {"entity_id": entity, "exchange": "nse", "exchange_code": symbol,
            "period_end": period.date().isoformat(), "public_date": public.isoformat(),
            "source_url": source_url + "#seqNumber=" + str(row["seqNumber"]),
            "date_is_imputed": 0, "needs_verification": 1,
            "is_synthetic": int(row.get("is_synthetic", 0))}


def import_filing_identities(config: Config) -> None:
    """Quarantine index claims and append identities from original bhavcopies."""
    if config.path("preregistration_lock").exists():
        raise RuntimeError("Identity inputs are registered; amendment required")
    allowed = set(read_manual(config, "events").entity_id) | set(read_manual(config, "peers").entity_id)
    # Research candidates need original identity proofs before classification
    # and selection. Their inclusion here only permits collection: index
    # claims remain quarantined and verification still requires original quotes.
    candidates_path = config.path("peer_discovery_candidates")
    if candidates_path.is_file():
        candidates = pd.read_csv(candidates_path)
        assert_real(candidates)
        allowed.update(candidates.entity_id.dropna())
    settings = config.section("financial_index_config")
    audit_path = config.path("financial_index_coverage")
    audit = pd.read_csv(audit_path) if audit_path.exists() else pd.DataFrame(columns=["status", "needs_verification"])
    client = CachedDownloader(config)
    fresh = []
    try:
        for window in audit.loc[audit.status.eq("cached_index") & audit.needs_verification.eq(0)].itertuples():
            raw = config.root / window.source_doc
            if raw.resolve().parent != (config.path("raw") / settings["source"]).resolve():
                raise ValueError("Financial index path is outside its configured cache")
            raw = client.fetch(settings["source"], window.source_url, raw.name, offline=True)
            if sha256_file(raw) != window.sha256 or window.is_synthetic != 0:
                raise ValueError("Financial index audit integrity failure")
            body = json.loads(raw.read_bytes())
            rows = body.get("data") if isinstance(body, dict) else body
            if not isinstance(rows, list):
                raise ValueError("Unrecognized financial-results index")
            for row in rows:
                identity = filing_identity(row, allowed, window.source_url, settings)
                if identity is not None:
                    fresh.append(identity)
    finally:
        client.close()
    columns = config.section("manual_config")["tables"]["security_crosswalk"]["columns"]
    fresh = pd.DataFrame(fresh, columns=columns).sort_values("public_date", kind="stable").drop_duplicates(
        ["entity_id", "exchange", "exchange_code"], keep="first")
    current = read_manual(config, "security_crosswalk")
    # Preserve the earlier imported claims as unresolved audit records. A
    # sequence-qualified index URL can itself have been constructed later.
    current.loc[current.source_url.str.startswith(settings["url"]), "needs_verification"] = 1
    market = market_as_of(config, pd.Timestamp.now(tz="UTC"))
    market = market.loc[market.entity_id.isin(allowed) & market.exchange.eq("nse") & market.series.eq("EQ")
                        & ~market.source_url.str.contains(";", regex=False)]
    first = market.sort_values("period_end").drop_duplicates(["entity_id", "symbol"], keep="first")
    originals = {}
    verified = []
    client = CachedDownloader(config)
    try:
        for row in first.itertuples():
            url = row.source_url
            if url not in originals:
                raw = client.fetch("nse", url, urlparse(url).path.rsplit("/", 1)[-1], offline=True)
                originals[url] = parse_bhavcopy(raw.read_bytes(), url, config.section("india_config")["market"])
            original = originals[url]
            proof = original.loc[original.entity_id.eq(row.entity_id) & original.symbol.eq(row.symbol)
                                 & original.series.eq("EQ") & original.needs_verification.eq(0)]
            if len(proof) != 1 or not proof.period_end.eq(row.period_end).all():
                raise ValueError("Processed identity differs from the original dated archive")
            proof = proof.iloc[0]
            verified.append({"entity_id": proof.entity_id, "exchange": "nse", "exchange_code": proof.symbol,
                             "period_end": proof.period_end.date().isoformat(), "public_date": proof.public_date.isoformat(),
                             "source_url": url, "date_is_imputed": int(proof.date_is_imputed),
                             "needs_verification": 0, "is_synthetic": int(proof.is_synthetic)})
    finally:
        client.close()
    fresh = pd.concat([fresh, pd.DataFrame(verified)], ignore_index=True)
    combined = pd.concat([current, fresh], ignore_index=True)
    combined["public_date"] = pd.to_datetime(combined.public_date, utc=True, format="mixed").map(lambda x: x.isoformat())
    combined = combined.drop_duplicates()
    if combined.duplicated(["entity_id", "exchange", "period_end", "public_date"]).any():
        raise ValueError("Historical identity conflict; no existing inputs overwritten")
    validate_table(combined, "security_crosswalk", config.section("manual_config"))
    write_real_table(combined, config.path("security_crosswalk"))
    LOG.info("Original quote identity proofs=%s; filing claims quarantined; total=%s dates_imputed=%s missing=%s", len(verified), len(combined),
             combined.date_is_imputed.sum(), combined.isna().sum().loc[lambda x: x.gt(0)].to_dict())
