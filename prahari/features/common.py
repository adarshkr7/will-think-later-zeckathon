"""Point-in-time feature contracts and guarded financial arithmetic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Value:
    value: float
    reason: str = ""


class MissingInput(ValueError):
    pass


def number(values: Mapping, name: str) -> float:
    value = values.get(name, np.nan)
    if value is None or pd.isna(value) or not np.isfinite(float(value)):
        raise MissingInput(f"missing:{name}")
    return float(value)


def divide(numerator: float, denominator: float, name: str = "denominator") -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator <= 0:
        raise MissingInput(f"invalid:{name}")
    return numerator / denominator


def evaluate(function: Callable[[], float]) -> Value:
    try:
        value = float(function())
        return Value(value) if np.isfinite(value) else Value(np.nan, "nonfinite_result")
    except MissingInput as exc:
        return Value(np.nan, str(exc))


def require_snapshot(table: pd.DataFrame) -> None:
    if "as_of" not in table.attrs or "max_source_date" not in table:
        raise ValueError("Features require a DataFrame returned by as_of")
    if pd.to_datetime(table.max_source_date, utc=True).ge(pd.Timestamp(table.attrs["as_of"])).any():
        raise ValueError("Feature source is not strictly before cutoff")


def financial_snapshot(table: pd.DataFrame, basis: str) -> pd.DataFrame:
    """Use one common FY per entity, with exact yearly lags; never mix fiscal years."""
    require_snapshot(table)
    data = table.loc[table.basis.eq(basis)].copy()
    rows = []
    for entity, group in data.groupby("entity_id", sort=True):
        end = group.period_end.max()
        record = {"entity_id": entity, "financial_period_end": end,
                  "max_source_date": group.max_source_date.max(),
                  "is_synthetic": int(group.is_synthetic.eq(1).any())}
        for lag in range(3):
            period = end - pd.DateOffset(years=lag)
            known = group.loc[group.period_end.eq(period)].sort_values("public_date").drop_duplicates("field", keep="last")
            suffix = "" if lag == 0 else f"_prev{lag}"
            record.update({str(row.field) + suffix: row.value for row in known.itertuples()})
        rows.append(record)
    result = pd.DataFrame(rows, columns=None if rows else ["entity_id", "financial_period_end", "max_source_date", "is_synthetic"])
    result.attrs.update(table.attrs)
    return result


def feature_frame(table: pd.DataFrame, functions: dict[str, Callable[[Mapping], Value]], *, financial_exempt: bool = False) -> pd.DataFrame:
    require_snapshot(table)
    rows = []
    for record in table.to_dict(orient="records"):
        row = {key: record[key] for key in ("entity_id", "max_source_date", "is_synthetic")}
        for name, function in functions.items():
            if financial_exempt and record.get("is_financial") == 1:
                value = Value(np.nan, "not_applicable_financial_firm")
            elif financial_exempt and pd.isna(record.get("is_financial", np.nan)):
                value = Value(np.nan, "classification_unknown")
            else:
                value = function(record)
            row[name], row[f"{name}__reason"] = value.value, value.reason
        rows.append(row)
    result = pd.DataFrame(rows, columns=["entity_id", "max_source_date", "is_synthetic", *[item for name in functions for item in (name, f"{name}__reason")]])
    result.attrs.update(table.attrs)
    return result
