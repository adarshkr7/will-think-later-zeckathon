"""Recover exact historical security identities from receipted NSE indexes."""

from __future__ import annotations

import json
import logging

import pandas as pd

from prahari.config import Config
from prahari.data.downloads import CachedDownloader
from prahari.data.firewall import write_real_table
from prahari.data.manual import read_manual
from prahari.data.quality import validate_table
from prahari.data.uci import sha256_file

LOG = logging.getLogger(__name__)


def filing_identity(row: dict, allowed: set[str], source_url: str, timezone: str) -> dict | None:
    """Use exact ISIN, reported symbol and latest stated dissemination time.

    Filing metadata establishes identity only. It does not certify financial
    statement values, sectors, or the availability of a separate annual report.
    Every supplied timestamp must parse; missing timing never becomes a lag.
    """
    entity = str(row.get("isin") or "").strip()
    symbol = str(row.get("symbol") or "").strip()
    if entity not in allowed or not symbol:
        return None
    raw_dates = [row.get(key) for key in ("exchdisstime", "broadCastDate", "filingDate")]
    dates = []
    for value in raw_dates:
        if value is None or str(value).strip() in ("", "-", "::"):
            continue
        date = pd.Timestamp(value)
        dates.append(date.tz_localize(timezone).tz_convert("UTC") if date.tzinfo is None else date.tz_convert("UTC"))
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
            "date_is_imputed": 0, "needs_verification": 0,
            "is_synthetic": int(row.get("is_synthetic", 0))}


def import_filing_identities(config: Config) -> None:
    """Append earliest observed exact mappings; preserve all existing inputs."""
    if config.path("preregistration_lock").exists():
        raise RuntimeError("Identity inputs are registered; amendment required")
    allowed = set(read_manual(config, "events").entity_id) | set(read_manual(config, "peers").entity_id)
    settings = config.section("financial_index_config")
    audit = pd.read_csv(config.path("financial_index_coverage"))
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
                identity = filing_identity(row, allowed, window.source_url, settings["timezone"])
                if identity is not None:
                    fresh.append(identity)
    finally:
        client.close()
    if not fresh:
        LOG.info("No usable historical identity filings; existing inputs preserved")
        return
    fresh = pd.DataFrame(fresh).sort_values("public_date", kind="stable").drop_duplicates(
        ["entity_id", "exchange", "exchange_code"], keep="first")
    current = read_manual(config, "security_crosswalk")
    combined = pd.concat([current, fresh], ignore_index=True)
    combined["public_date"] = pd.to_datetime(combined.public_date, utc=True, format="mixed").map(lambda x: x.isoformat())
    combined = combined.drop_duplicates()
    if combined.duplicated(["entity_id", "exchange", "period_end", "public_date"]).any():
        raise ValueError("Historical identity conflict; no existing inputs overwritten")
    validate_table(combined, "security_crosswalk", config.section("manual_config"))
    write_real_table(combined, config.path("security_crosswalk"))
    LOG.info("Historical identity candidates=%s total=%s dates_imputed=%s missing=%s", len(fresh), len(combined),
             combined.date_is_imputed.sum(), combined.isna().sum().loc[lambda x: x.gt(0)].to_dict())
