"""Historical NSE observations retain delisted ISINs and original provenance."""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.downloads import CachedDownloader
from prahari.data.firewall import write_real_table

LOG = logging.getLogger(__name__)


def archive_url(day: str | pd.Timestamp, settings: dict) -> tuple[str, str]:
    date = pd.Timestamp(day)
    month = settings["months"][date.month - 1]
    url = settings["legacy_url"].format(year=date.year, month=month, day=f"{date.day:02d}")
    return url, url.rsplit("/", 1)[-1]


def parse_bhavcopy(payload: bytes, source_url: str, settings: dict) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError("Expected one CSV in historical bhavcopy")
        table = pd.read_csv(archive.open(members[0]))
    table.columns = table.columns.str.strip()
    mapping = settings["legacy_columns"]
    symbol_only = False
    if not set(mapping).issubset(table):
        missing = set(mapping).difference(table)
        if missing == {"ISIN"} and set(settings["symbol_only_columns"]).issubset(table):
            mapping = settings["symbol_only_columns"]
            symbol_only = True
        else:
            raise ValueError("Unsupported official bhavcopy schema")
    keep = list(mapping) + (["is_synthetic"] if "is_synthetic" in table else [])
    table = table[keep].rename(columns=mapping)
    table["series"] = table.series.str.strip()
    table = table.loc[table.series.isin(settings["series"])].copy()
    table["period_end"] = pd.to_datetime(table.period_end, format="%d-%b-%Y", utc=True)
    table["public_date"] = table.period_end + pd.Timedelta(days=settings["publication_lag_days"])
    table["symbol"] = table.symbol.str.strip()
    if symbol_only:
        table["exchange_code"] = table.symbol
        table["entity_id"] = "NSE:" + table.symbol
    else:
        table["entity_id"] = table.entity_id.str.strip()
    for column in ("close", "volume"):
        table[column] = pd.to_numeric(table[column], errors="raise")
    if table.entity_id.isna().any() or table.close.le(0).any() or table.volume.lt(0).any():
        raise ValueError("Invalid market observation; do not fill it with zero")
    if table.duplicated(["entity_id", "period_end", "series"]).any():
        raise ValueError("Duplicate bhavcopy security/session")
    table["source_url"] = source_url
    table["date_is_imputed"] = 1  # Daily archive publication time unknown; next-day conservative dating.
    table["needs_verification"] = int(symbol_only)
    table["identity_reason"] = "unmapped_legacy_symbol" if symbol_only else ""
    table["exchange"] = "nse"
    if "is_synthetic" not in table:
        table["is_synthetic"] = 0
    LOG.info("Bhavcopy rows=%s dates_imputed=%s missing=%s", len(table), len(table), table.isna().sum().to_dict())
    return table


def cache_session(config: Config, downloader: CachedDownloader, day: str, *, offline: bool) -> pd.DataFrame:
    settings = config.section("india_config")["market"]
    url, filename = archive_url(day, settings)
    raw = downloader.fetch("nse", url, filename, offline=offline)
    table = parse_bhavcopy(raw.read_bytes(), url, settings)
    if table.needs_verification.eq(1).any():
        from prahari.data.manual import read_manual
        mapping = as_of(read_manual(config, "security_crosswalk"), pd.to_datetime(day, utc=True) + pd.Timedelta(days=settings["publication_lag_days"]+1))
        mapping = mapping.loc[mapping.exchange.eq("nse")].sort_values(["period_end", "public_date"]).drop_duplicates("exchange_code", keep="last").set_index("exchange_code")
        resolved = table.exchange_code.map(mapping.entity_id)
        known = resolved.notna()
        table.loc[known, "entity_id"] = resolved.loc[known]
        table.loc[known, "needs_verification"] = 0
        table.loc[known, "identity_reason"] = ""
        if known.any():
            dates = pd.to_datetime(table.exchange_code.map(mapping.public_date), utc=True)
            table["public_date"] = table.public_date.where(dates.isna() | table.public_date.ge(dates), dates)
            evidence = table.exchange_code.map(mapping.source_url)
            table.loc[known, "source_url"] = table.loc[known, "source_url"] + ";" + evidence.loc[known]
            table.loc[known & table.exchange_code.map(mapping.is_synthetic).eq(1), "is_synthetic"] = 1
    if not table.period_end.eq(pd.to_datetime(day, utc=True)).all():
        raise ValueError("NSE archive observations do not match the requested date")
    write_real_table(table, config.path("market_cache") / f"bhavcopy_{pd.Timestamp(day):%Y%m%d}.parquet")
    return table


def parse_index(payload: bytes, source_url: str, settings: dict) -> pd.DataFrame:
    table = pd.read_csv(io.BytesIO(payload))
    table.columns = table.columns.str.strip()
    mapping = settings["index_columns"]
    if not set(mapping).issubset(table):
        raise ValueError("Unsupported historical index schema")
    keep = list(mapping) + (["is_synthetic"] if "is_synthetic" in table else [])
    table = table[keep].rename(columns=mapping)
    table["name"] = table.name.str.strip()
    aliases = {name.casefold(): canonical for name, canonical in settings.get("index_aliases", {}).items()}
    table["source_index_name"] = table.name
    table["name"] = table.name.map(lambda name: aliases.get(name.casefold(), name))
    table = table.loc[table.name.str.casefold().isin([name.casefold() for name in settings["index_names"]])].copy()
    table["entity_id"] = table.name.str.casefold().str.replace(" ", "_", regex=False)
    table["period_end"] = pd.to_datetime(table.period_end.str.replace("/", "-", regex=False), format="%d-%m-%Y", utc=True)
    table["public_date"] = table.period_end + pd.Timedelta(days=settings["publication_lag_days"])
    table["close"] = pd.to_numeric(table.close, errors="raise")
    if table.empty or table.close.isna().any() or table.close.le(0).any():
        raise ValueError("Requested historical index is absent or invalid")
    table["return_basis"] = "price_index"  # Never claim the archive is TRI.
    table["source_url"], table["date_is_imputed"] = source_url, 1
    table["needs_verification"] = 0
    if "is_synthetic" not in table:
        table["is_synthetic"] = 0
    return table


def market_as_of(config: Config, t: str | pd.Timestamp) -> pd.DataFrame:
    files = sorted([*config.path("market_cache").glob("bhavcopy_*.parquet"),
                    *config.path("market_cache").glob("bse_*.parquet")])
    if not files:
        raise FileNotFoundError("No market cache; run scripts.02_market_data")
    tables = []
    for path in files:
        table = pd.read_parquet(path)
        if "exchange" not in table:
            table["exchange"] = "bse" if path.name.startswith("bse_") else "nse"
        tables.append(table)
    return as_of(pd.concat(tables, ignore_index=True), t)


def bounded_forward_fill(table: pd.DataFrame, sessions: pd.DatetimeIndex, limit: int) -> pd.DataFrame:
    """Carry a last observed quote for at most configured actual exchange sessions.

    Keep the original source date; never back-fill, invent volume, or extend a
    delisted name beyond its documented listing window (caller supplies sessions).
    """
    if "as_of" not in table.attrs:
        raise ValueError("Price filling requires as_of-filtered observations")
    if table.entity_id.nunique() != 1 or table.period_end.duplicated().any() or limit <= 0:
        raise ValueError("Fill one security at a time with a positive session limit")
    if not (sessions < pd.to_datetime(table.attrs["as_of"], utc=True)).all():
        raise ValueError("Cannot carry prices into future scoring sessions")
    result = table.set_index("period_end").reindex(sessions).copy()
    observed = result.close.notna()
    for column in ("close", "entity_id", "symbol", "public_date", "max_source_date", "source_url",
                   "date_is_imputed", "needs_verification", "is_synthetic"):
        if column in result:
            result[column] = result[column].ffill(limit=limit)
    result["price_is_carried"] = (~observed & result.close.notna()).astype(int)
    for column in ("entity_id", "symbol", "is_synthetic"):
        if column in result:
            result[column] = result[column].fillna(table[column].iloc[0])
    result["needs_verification"] = result["needs_verification"].where(result.close.notna(), 1)
    result["price_missing_reason"] = ""
    result.loc[result.close.isna(), "price_missing_reason"] = "no_quote_within_session_limit"
    result.index.name = "period_end"
    return result.reset_index()
