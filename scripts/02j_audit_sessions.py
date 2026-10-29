"""Audit/recover actual NSE sessions against independently published cash totals."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.bhavcopy import archive_url, cache_session, parse_bhavcopy, parse_index
from prahari.data.downloads import CachedDownloader, SourceUnavailable
from prahari.data.firewall import assert_real, write_real_table
from prahari.data.manual import read_manual
from prahari.data.quality import validate_table
from prahari.data.session_calendar import certify_period, reviewed_session_counts
from prahari.data.uci import sha256_file

LOG = logging.getLogger(__name__)
SESSION_COLUMNS = ["entity_id", "period_end", "public_date", "source_url", "source_sha256", "rows",
                   "date_is_imputed", "needs_verification", "is_synthetic"]


def session_record(config: Config, client: CachedDownloader, day: pd.Timestamp) -> dict:
    """Prove the exchange traded, independently of unresolved company identifiers."""
    market = config.section("india_config")["market"]
    url, filename = archive_url(day, market)
    raw = client.fetch("nse", url, filename, offline=True)
    table = parse_bhavcopy(raw.read_bytes(), url, market)
    assert_real(table)
    if table.empty or not table.period_end.eq(day).all() or not table.volume.gt(0).any():
        raise ValueError("Archive does not prove an actual equity trading session")
    return {"entity_id": config.section("calendar_config")["exchange"], "period_end": day,
            "public_date": day+pd.Timedelta(days=market["publication_lag_days"]),
            "source_url": url, "source_sha256": sha256_file(raw), "rows": len(table),
            "date_is_imputed": 1, "needs_verification": 0, "is_synthetic": 0}


def read_sessions(config: Config, client: CachedDownloader) -> pd.DataFrame:
    market = config.section("india_config")["market"]
    rows = []
    for receipt in sorted((config.path("raw") / "nse").glob("*.receipt.json")):
        filename = receipt.name.removesuffix(".receipt.json")
        match = re.fullmatch(r"cm(\d{2})([A-Z]{3})(\d{4})bhav\.csv\.zip", filename)
        if match is None:
            raise ValueError("Unsupported NSE session archive filename")
        day, month, year = match.groups()
        date = pd.Timestamp(year=int(year), month=market["months"].index(month)+1, day=int(day), tz="UTC")
        rows.append(session_record(config, client, date))
    LOG.info("Original session proofs=%s dates_imputed=%s missing_identifiers_do_not_certify_company_identity",
             len(rows), len(rows))
    return pd.DataFrame(rows, columns=SESSION_COLUMNS)


def weekday_requests_complete(config: Config, first: pd.Timestamp, last: pd.Timestamp) -> bool:
    """Check request coverage only; a negative receipt is never a closure proof."""
    settings = config.section("india_config")["market"]
    for day in pd.date_range(first, last, freq="B"):
        url, filename = archive_url(day, settings)
        raw = config.path("raw") / "nse" / filename
        if raw.with_suffix(raw.suffix+".receipt.json").exists():
            continue
        absent = raw.with_suffix(raw.suffix+".unavailable.json")
        if not absent.exists():
            return False
        proof = json.loads(absent.read_text(encoding="utf-8"))
        if proof.get("source_url") != url or proof.get("http_status") != 404:
            raise ValueError("Invalid negative request receipt")
    return True


def periods(config: Config, counts: pd.DataFrame):
    market = config.section("india_config")["market"]
    begin, finish = [pd.to_datetime(market[name], utc=True) for name in ("start_date", "end_date")]
    pairs = counts[["period_start", "period_end"]].drop_duplicates().sort_values("period_end")
    for row in pairs.itertuples():
        first, last = pd.to_datetime(row.period_start, utc=True), pd.to_datetime(row.period_end, utc=True)
        if begin <= first <= last <= finish:
            yield first, last


def recover(config: Config, client: CachedDownloader, sessions: pd.DataFrame,
            claims: pd.DataFrame, now: pd.Timestamp) -> pd.DataFrame:
    settings = config.section("calendar_config")
    market = config.section("india_config")["market"]
    priorities = {month: order for order, month in enumerate(settings["recovery_month_priority"])}
    for first, last in periods(config, claims):
        _, status = certify_period(as_of(sessions, now), claims, first, last, settings["exchange"], "pending")
        if status["status"] != "incomplete_census":
            continue
        if not weekday_requests_complete(config, first, last):
            LOG.info("Weekday acquisition incomplete for %s; weekend recovery deferred", last.date())
            continue
        known = set(sessions.period_end)
        candidates = [day for day in pd.date_range(first, last, freq="D") if day.day_of_week >= 5 and day not in known]
        candidates.sort(key=lambda day: (priorities[day.month], day))
        for day in candidates:
            try:
                cache_session(config, client, str(day.date()), offline=False)
            except SourceUnavailable:
                continue
            record = session_record(config, client, day)
            sessions = pd.concat([sessions, pd.DataFrame([record])], ignore_index=True)
            index_url = market["index_url"].format(date=day.strftime("%d%m%Y"))
            try:
                raw = client.fetch("nse_index", index_url, index_url.rsplit("/", 1)[-1])
                index = parse_index(raw.read_bytes(), index_url, market)
                if not index.period_end.eq(day).all():
                    raise ValueError("Recovered index date differs from requested session")
                write_real_table(index, config.path("market_cache") / f"index_{day:%Y%m%d}.parquet")
            except SourceUnavailable:
                LOG.warning("Actual session %s has no cached official index; no zero return substituted", day.date())
            _, status = certify_period(as_of(sessions, now), claims, first, last, settings["exchange"], "pending")
            LOG.info("Session recovery %s observed=%s published=%s status=%s", last.date(),
                     status["observed_sessions"], status["expected_sessions"], status["status"])
            if status["status"] != "incomplete_census":
                break
    return sessions


def write_audit(config: Config, sessions: pd.DataFrame, claims: pd.DataFrame, now: pd.Timestamp) -> None:
    settings = config.section("calendar_config")
    visible = as_of(sessions, now)
    assert_real(visible)
    assert_real(claims)
    calendars, audits = [], []
    config.path("session_census").mkdir(parents=True, exist_ok=True)
    for first, last in periods(config, claims):
        actual = visible.loc[visible.period_end.between(first, last)]
        views = claims.loc[claims.period_end.eq(last)]
        payload = {"method": settings["method_id"], "exchange": settings["exchange"],
                   "period_start": first.isoformat(), "period_end": last.isoformat(), "is_synthetic": 0,
                   "sessions": actual[SESSION_COLUMNS].to_dict(orient="records"),
                   "count_claims": views.drop(columns="max_source_date").to_dict(orient="records")}
        body = json.dumps(payload, sort_keys=True, indent=2, default=str).encode("utf-8")
        digest = hashlib.sha256(body).hexdigest()
        path = config.path("session_census") / settings["census_filename"].format(
            exchange=settings["exchange"], period_end=str(last.date()), sha256=digest)
        if path.exists() and path.read_bytes() != body:
            raise ValueError("Immutable session-census receipt changed")
        if not path.exists():
            temporary = path.with_suffix(path.suffix+".partial")
            temporary.write_bytes(body)
            temporary.replace(path)
        ref = path.relative_to(config.root).as_posix()+"#sha256="+digest
        calendar, audit = certify_period(visible, claims, first, last, settings["exchange"], ref)
        calendar["derivation_method"] = settings["method_id"]
        calendars.append(calendar)
        audits.append({**audit, "census_doc": path.relative_to(config.root).as_posix(), "census_sha256": digest})
    fresh = pd.concat(calendars, ignore_index=True)
    target = config.path("manual") / "trading_calendar.csv"
    current = read_manual(config, "trading_calendar")
    # Rebuild only this derivation's rows. A later conflicting source cannot
    # leave a stale closed-date certificate visible; human rows are preserved.
    current = current.loc[current.derivation_method.fillna("").ne(settings["method_id"])]
    combined = pd.concat([current, fresh], ignore_index=True)
    for name in ("period_end", "public_date"):
        combined[name] = pd.to_datetime(combined[name], utc=True, format="mixed").map(lambda day: day.isoformat())
    keys = ["entity_id", "period_end", "public_date"]
    combined = combined.drop_duplicates()
    if combined.duplicated(keys).any():
        raise ValueError("Calendar proof conflicts with existing observations; review required")
    validate_table(combined, "trading_calendar", config.section("manual_config"))
    write_real_table(combined, target)
    write_real_table(pd.DataFrame(audits), config.path("session_coverage"))
    LOG.info("Calendar rows=%s source-verified closed dates=%s dates_imputed=%s",
             len(combined), combined.is_trading_day.eq(0).sum(), combined.date_is_imputed.sum())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--recover-missing", action="store_true")
    args = parser.parse_args()
    if args.offline and args.recover_missing:
        parser.error("Recovery requires online mode")
    config = Config(args.config)
    config.setup_logging()
    if config.path("preregistration_lock").exists():
        raise RuntimeError("Calendar inputs are registered; amendment required")
    client = CachedDownloader(config)
    try:
        fresh = reviewed_session_counts(config, client, offline=args.offline)
        target = config.path("manual") / "trading_session_counts.csv"
        old = pd.read_csv(target) if target.exists() else fresh.iloc[:0]
        counts = pd.concat([old, fresh], ignore_index=True).drop_duplicates()
        if counts.duplicated(["entity_id", "field", "period_end", "public_date"]).any():
            raise ValueError("Conflicting source-count observations")
        validate_table(counts, "trading_session_counts", config.section("manual_config"))
        write_real_table(counts, target)
        now = pd.Timestamp.now(tz="UTC")
        claims = as_of(counts, now)
        sessions = read_sessions(config, client)
        if args.recover_missing:
            sessions = recover(config, client, sessions, claims, now)
        write_audit(config, sessions, claims, now)
    finally:
        client.close()


if __name__ == "__main__":
    main()
