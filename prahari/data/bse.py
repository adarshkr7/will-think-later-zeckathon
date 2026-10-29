"""Legacy BSE fallback, preserving unverified identity mappings explicitly."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.downloads import CachedDownloader
from prahari.data.firewall import write_real_table


def parse_bse(payload: bytes, source_url: str, day: str, settings: dict) -> pd.DataFrame:
    """BSE legacy headers; reference: sdabhi23/bsedata's original bhavcopy reader.

    SC_CODE is an exchange code, not an ISIN. Never guess issuer identities or
    join by a similar company name. Unmapped rows remain needs_verification=1.
    """
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError("Expected one BSE CSV")
        expected = settings["bse_member"].format(date=pd.Timestamp(day).strftime("%d%m%y"))
        if Path(members[0]).name.upper() != expected.upper():
            raise ValueError("BSE archive member does not match the requested date")
        table = pd.read_csv(archive.open(members[0]), dtype={"SC_CODE": str})
    table.columns = table.columns.str.strip()
    mapping = settings["bse_columns"]
    if not set(mapping).issubset(table):
        raise ValueError("Unrecognized BSE bhavcopy schema")
    keep = list(mapping) + (["is_synthetic"] if "is_synthetic" in table else [])
    table = table[keep].rename(columns=mapping)
    table = table.loc[table.security_type.eq(settings["bse_equity_type"])].copy()
    table["entity_id"] = "BSE:" + table.exchange_code.astype(str)
    table["symbol"] = table.symbol.str.strip()
    table["series"] = settings["bse_equity_type"]
    table["exchange"] = "bse"
    table["period_end"] = pd.to_datetime(day, utc=True)
    table["public_date"] = table.period_end + pd.Timedelta(days=settings["publication_lag_days"])
    table["close"] = pd.to_numeric(table.close, errors="raise")
    table["volume"] = pd.to_numeric(table.volume, errors="raise")
    if (not np.isfinite(table[["close", "volume"]].to_numpy(dtype=float)).all()
            or table.close.le(0).any() or table.volume.lt(0).any()):
        raise ValueError("Invalid BSE prices or volumes")
    table["source_url"] = source_url
    table["needs_verification"], table["date_is_imputed"] = 1, 1
    table["identity_reason"] = "unmapped_exchange_code"
    if "is_synthetic" not in table:
        table["is_synthetic"] = 0
    return table


def cache_bse_session(config: Config, downloader: CachedDownloader, day: str, *, offline: bool) -> pd.DataFrame:
    settings = config.section("india_config")["market"]
    url = settings["bse_url"].format(date=pd.Timestamp(day).strftime("%d%m%y"))
    raw = downloader.fetch("bse", url, url.rsplit("/", 1)[-1], offline=offline)
    table = parse_bse(raw.read_bytes(), url, day, settings)
    path = config.path("security_crosswalk")
    if path.exists():
        crosswalk = pd.read_csv(path, dtype={"exchange_code": str})
        eligible = as_of(crosswalk, pd.Timestamp(day, tz="UTC") + pd.Timedelta(days=settings["publication_lag_days"] + 1))
        eligible = eligible.loc[eligible.exchange.eq("bse")]
        eligible = eligible.sort_values(["period_end", "public_date"]).drop_duplicates("exchange_code", keep="last")
        mapping = eligible.set_index("exchange_code").entity_id
        if not mapping.index.is_unique:
            raise ValueError("Ambiguous dated BSE identity mapping")
        mapped = table.exchange_code.map(mapping)
        known = mapped.notna()
        table.loc[known, "entity_id"] = mapped.loc[known]
        table.loc[known, "needs_verification"] = 0
        table.loc[known, "identity_reason"] = ""
        if known.any():
            identity_dates = pd.to_datetime(table.exchange_code.map(eligible.set_index("exchange_code").public_date), utc=True)
            table["public_date"] = table.public_date.where(identity_dates.isna() | table.public_date.ge(identity_dates), identity_dates)
            identity_sources = table.exchange_code.map(eligible.set_index("exchange_code").source_url)
            table.loc[known, "source_url"] = table.loc[known, "source_url"] + ";" + identity_sources.loc[known]
            identity_taint = table.exchange_code.map(eligible.set_index("exchange_code").is_synthetic)
            table.loc[known & identity_taint.eq(1), "is_synthetic"] = 1
    write_real_table(table, config.path("market_cache") / f"bse_{pd.Timestamp(day):%Y%m%d}.parquet")
    return table
