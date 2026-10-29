"""The only point-in-time access boundary for Indian observation tables."""

from __future__ import annotations

import pandas as pd


def as_of(table: pd.DataFrame, t: str | pd.Timestamp) -> pd.DataFrame:
    """Return latest public observation per entity, field, period and basis.

    Retain historical periods for lagged ratios; restatements supersede earlier
    versions only when they were public strictly before t. Long-form rows must
    name their field. Wide-form rows use the entity/period/basis key.
    """
    required = {"entity_id", "period_end", "public_date", "date_is_imputed",
                "needs_verification", "is_synthetic"}
    if missing := required.difference(table.columns):
        raise ValueError(f"Point-in-time columns missing: {sorted(missing)}")
    for column in ("is_synthetic", "date_is_imputed", "needs_verification"):
        if table[column].isna().any() or not table[column].isin([0, 1]).all():
            raise ValueError(f"Invalid {column} flags")
    result = table.copy()
    result["public_date"] = pd.to_datetime(result["public_date"], errors="raise", utc=True, format="mixed")
    result["period_end"] = pd.to_datetime(result["period_end"], errors="raise", utc=True)
    if result[["entity_id", "period_end", "public_date"]].isna().any().any():
        raise ValueError("Unknown dates must be conservatively imputed before as_of")
    instant = pd.to_datetime(t, utc=True)
    result = result.loc[result["public_date"].lt(instant) & result["period_end"].lt(instant)
                        & result["needs_verification"].eq(0)].copy()
    source_columns = [c for c in ("source_url", "source_doc", "source_urls") if c in result]
    has_source = result[source_columns].apply(
        lambda column: column.notna() & column.astype(str).str.strip().ne("")
    ).any(axis=1)
    if not source_columns or (len(result) and not has_source.all()):
        raise ValueError("Every visible Indian observation needs source provenance")
    key = [c for c in ("entity_id", "field", "period_start", "period_end", "basis", "instrument", "agency", "event_type", "series", "exchange")
           if c in result]
    if result.duplicated(key + ["public_date"]).any():
        raise ValueError("Ambiguous duplicate source versions")
    result = result.sort_values("public_date", kind="stable").drop_duplicates(key, keep="last")
    result["max_source_date"] = result["public_date"]
    result.attrs["as_of"] = instant.isoformat()
    return result.reset_index(drop=True)


def impute_public_dates(table: pd.DataFrame, *, lag_days: int) -> pd.DataFrame:
    """Apply configured FY-end lags, marking every imputed dissemination date."""
    if lag_days <= 0:
        raise ValueError("Publication lag must be positive")
    result = table.copy()
    public = pd.to_datetime(result["public_date"], utc=True)
    periods = pd.to_datetime(result["period_end"], utc=True)
    missing = public.isna()
    result["public_date"] = public.fillna(periods + pd.to_timedelta(lag_days, unit="D"))
    result["date_is_imputed"] = result["date_is_imputed"].where(~missing, 1)
    return result
