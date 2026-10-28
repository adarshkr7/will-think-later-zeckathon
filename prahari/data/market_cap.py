"""Point-in-time price/share joins; no assumed or back-filled share counts."""

from __future__ import annotations

import numpy as np
import pandas as pd


def market_cap(prices: pd.DataFrame, shares: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Market equity = close price × shares outstanding, in matching units.

    NSE market-cap methodology: market capitalization equals price multiplied
    by outstanding equity shares (NSE indices methodology). Both inputs must
    be dated, as_of-filtered observations; missing shares produce NaN, not an
    assumed share count. Filing provenance survives the join.
    """
    if "as_of" not in prices.attrs or "as_of" not in shares.attrs:
        raise ValueError("Market cap requires two as_of snapshots")
    cutoff = pd.to_datetime(prices.attrs["as_of"], utc=True)
    if cutoff != pd.to_datetime(shares.attrs["as_of"], utc=True):
        raise ValueError("Price and filing cutoffs differ")
    for table in (prices, shares):
        if not pd.to_datetime(table.max_source_date, utc=True).lt(cutoff).all():
            raise ValueError("Future input to market cap")
    price = prices.copy()
    if "source_url" not in price:
        price["source_url"] = pd.NA
    if "source_doc" not in price:
        price["source_doc"] = pd.NA
    price = price.rename(columns={"source_doc": "price_source_doc"})
    price["exchange_priority"] = price["exchange"].map({name: index for index, name in enumerate(settings["exchange_preference"])}) if "exchange" in price else 0
    price["series_priority"] = price.series.map({name: index for index, name in enumerate(settings["series"])})
    price["series_priority"] = price.series_priority.fillna(len(settings["series"]))
    price = price.sort_values(["period_end", "exchange_priority", "series_priority"], ascending=[True, False, False]).drop_duplicates("entity_id", keep="last")
    filing = shares.loc[shares.field.eq("shares_outstanding")].sort_values(["period_end", "public_date"])
    filing = filing.drop_duplicates("entity_id", keep="last")
    filing = filing[["entity_id", "value", "max_source_date", "source_doc", "is_synthetic", "date_is_imputed"]].rename(
        columns={"value": "shares_outstanding", "max_source_date": "shares_source_date", "is_synthetic": "shares_synthetic", "source_doc": "shares_source_doc", "date_is_imputed": "shares_date_imputed"})
    result = price.merge(filing, how="left", on="entity_id", validate="one_to_one")
    counts = pd.to_numeric(result.shares_outstanding, errors="raise")
    valid = counts.gt(0) & result.close.gt(0) & np.isfinite(counts) & np.isfinite(result.close)
    result["market_cap"] = (result.close * counts).where(valid)
    result["market_cap_reason"] = ""
    result.loc[~valid, "market_cap_reason"] = "invalid_price_or_share_count"
    result.loc[counts.isna(), "market_cap_reason"] = "missing_public_share_count"
    overflow = result.market_cap.notna() & ~np.isfinite(result.market_cap)
    result.loc[overflow, "market_cap"] = np.nan
    result.loc[overflow, "market_cap_reason"] = "non_finite_product"
    result["max_source_date"] = result.max_source_date.where(
        result.shares_source_date.isna() | result.max_source_date.ge(result.shares_source_date), result.shares_source_date)
    result["is_synthetic"] = (result.is_synthetic.eq(1) | result.shares_synthetic.eq(1)).astype(int)
    result["source_doc"] = result.shares_source_doc.combine_first(result.price_source_doc)
    result["public_date"] = result.max_source_date
    result["date_is_imputed"] = (result.date_is_imputed.eq(1) | result.shares_date_imputed.eq(1)).astype(int)
    result["needs_verification"] = result.market_cap.isna().astype(int)
    return result[["entity_id", "period_end", "public_date", "date_is_imputed", "needs_verification", "market_cap", "market_cap_reason", "max_source_date", "source_url", "source_doc",
                   "price_source_doc", "shares_source_doc", "is_synthetic"]]
