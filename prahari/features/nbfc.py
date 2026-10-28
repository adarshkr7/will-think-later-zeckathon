"""Predeclared monotone financial-firm scorecard; no Indian-label fitting."""

from __future__ import annotations

import numpy as np
import pandas as pd

from prahari.features.common import divide, evaluate, number, require_snapshot


def nbfc_features(table: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Plan §3.5 fixed scorecard, source variables retained with unknown reasons.

    CAR headroom requires a sourced date-applicable regulatory minimum in
    car_minimum_pct. No timeless minimum is assumed for NBFC/HFC subtypes.
    All ranks use only the current financial-firm cross-section.
    """
    require_snapshot(table)
    result = table[["entity_id", "is_financial", "max_source_date", "is_synthetic"]].copy()
    functions = {"leverage": lambda v: divide(number(v, "total_assets"), number(v, "equity"), "equity"),
                 "cp_share_of_borrowings": lambda v: number(v, "cp_share_of_borrowings"),
                 "st_liab_to_st_assets": lambda v: number(v, "st_liab_to_st_assets"),
                 "gnpa_pct": lambda v: number(v, "gnpa_pct"),
                 "gnpa_delta": lambda v: number(v, "gnpa_pct") - number(v, "gnpa_pct_prev1"),
                 "car_headroom": lambda v: number(v, "car_pct") - number(v, "car_minimum_pct"),
                 "nim_delta": lambda v: number(v, "nim_pct") - number(v, "nim_pct_prev1"),
                 "loan_growth_anomaly": lambda v: number(v, "loan_book_growth") - number(v, "peer_loan_growth_median")}
    records = table.to_dict(orient="records")
    for name, function in functions.items():
        values = [evaluate(lambda v=v: function(v)) for v in records]
        result[name] = [value.value for value in values]
        result[name + "__reason"] = [value.reason for value in values]
        mask = result.is_financial.eq(1) & result[name].notna()
        count = int(mask.sum())
        ranks = (result.loc[mask, name].rank(method="average") - 0.5) / count if count else pd.Series(dtype=float)
        if settings["directions"][name] < 0:
            ranks = 1 - ranks
        result[name + "__rank"] = ranks.reindex(result.index) if count >= settings["minimum_cross_section"] else np.nan
    columns = [name + "__rank" for name in functions]
    weights = np.asarray([settings["weights"][name] for name in functions], dtype=float)
    if not np.isfinite(weights).all() or (weights < 0).any() or weights.sum() <= 0:
        raise ValueError("NBFC weights must be finite, nonnegative and nonempty")
    complete = result[columns].notna().all(axis=1) & result.is_financial.eq(1)
    result["nbfc_score"] = result[columns].mul(weights).sum(axis=1).div(weights.sum()).where(complete)
    result["nbfc_score__reason"] = np.where(complete, "", "incomplete_financial_scorecard_or_cross_section")
    result.loc[result.is_financial.eq(0), "nbfc_score__reason"] = "not_applicable_nonfinancial_firm"
    result = result.drop(columns="is_financial")
    result.attrs.update(table.attrs)
    return result
