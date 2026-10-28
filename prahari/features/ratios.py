"""Exact harmonized ratios and accounting overlays, with guarded denominators."""

from __future__ import annotations

from typing import Mapping

import pandas as pd

from prahari.features.common import Value, divide, evaluate, feature_frame, number


def ratio(values: Mapping, numerator: str, denominator: str) -> Value:
    return evaluate(lambda: divide(number(values, numerator), number(values, denominator), denominator))


def harmonized_ratios(table: pd.DataFrame) -> pd.DataFrame:
    """UCI 365 attribute definitions; mappings are in harmonized_map.yaml.

    These are raw ratios. The Indian cross-section rank is computed later,
    without fitting any transform on future quarters or Indian labels.
    """
    simple = {"roa": ("pat", "total_assets"), "tl_ta": ("total_liabilities", "total_assets"),
              "current_ratio": ("current_assets", "current_liabilities"), "re_ta": ("retained_earnings", "total_assets"),
              "ebit_ta": ("ebit", "total_assets"), "equity_tl": ("equity", "total_liabilities"),
              "sales_ta": ("revenue", "total_assets"), "equity_ta": ("equity", "total_assets"),
              "cl_ta": ("current_liabilities", "total_assets"), "cash_ta": ("cash_and_st_investments", "total_assets"),
              "sales_growth": ("revenue", "revenue_prev1"), "cwip_ta": ("cwip", "total_assets"),
              "interest_coverage": ("ebit", "interest_expense"),
              "consolidated_standalone_debt": ("consolidated_total_debt", "total_debt")}
    functions = {name: (lambda values, pair=pair: ratio(values, *pair)) for name, pair in simple.items()}
    functions.update({
        "wc_ta": lambda v: evaluate(lambda: divide(number(v, "current_assets") - number(v, "current_liabilities"), number(v, "total_assets"), "total_assets")),
        "quick_ratio": lambda v: evaluate(lambda: divide(number(v, "current_assets") - number(v, "inventory"), number(v, "current_liabilities"), "current_liabilities")),
        "gp_dep_tl": lambda v: evaluate(lambda: divide(number(v, "gross_profit") + number(v, "depreciation"), number(v, "total_liabilities"), "total_liabilities")),
        "alm_mismatch": lambda v: evaluate(lambda: divide(number(v, "st_borrowings") + number(v, "commercial_paper"), number(v, "cash_and_st_investments") + number(v, "receivables"), "liquid_assets")),
        "cash_conversion_gap": lambda v: evaluate(lambda: divide(number(v, "pat") - number(v, "cfo"), number(v, "total_assets"), "total_assets")),
    })
    return feature_frame(table, functions, financial_exempt=True)
