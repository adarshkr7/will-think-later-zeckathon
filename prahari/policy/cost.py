"""Expected and realized policy costs, with missing scores never treated as zero."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def expected_cost(probabilities: np.ndarray, selected: np.ndarray, settings: dict) -> float:
    """Bayes decision loss: sum FN_cost*p outside + FP_cost*(1-p) inside."""
    p, flag = np.asarray(probabilities, dtype=float), np.asarray(selected, dtype=bool)
    if p.shape != flag.shape or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        return float("nan")
    return float(np.where(flag, settings["cost_fp"] * (1 - p), settings["cost_fn"] * p).sum())


def realized_cost(labels: np.ndarray, selected: np.ndarray, settings: dict) -> float:
    """Realized policy loss, defined only for complete binary outcomes."""
    y, flag = np.asarray(labels), np.asarray(selected, dtype=bool)
    if y.shape != flag.shape or not np.isin(y, [0, 1]).all():
        return float("nan")
    return float(settings["cost_fn"] * ((y == 1) & ~flag).sum() + settings["cost_fp"] * ((y == 0) & flag).sum())


def cost_curve(probabilities: np.ndarray, settings: dict, extra_slots: int, *, is_synthetic: int, ordered: bool = False) -> pd.DataFrame:
    """Descriptive budget curve and marginal shadow prices; never tunes the cap."""
    p = np.asarray(probabilities, dtype=float)
    if not ordered:
        p = np.sort(p)[::-1]
    cap = math.floor(settings["alert_frac"] * len(p))
    rows = []
    for count in range(min(len(p), max(2 * cap, cap + extra_slots)) + 1):
        selected = np.arange(len(p)) < count
        cost = expected_cost(p, selected, settings)
        marginal = (settings["cost_fn"] + settings["cost_fp"]) * p[count] - settings["cost_fp"] if count < len(p) and np.isfinite(p[count]) else np.nan
        rows.append({"k": count, "registered_cap": cap, "expected_cost": cost, "next_slot_benefit": marginal,
                     "is_counterfactual_budget": int(count > cap), "needs_verification": int(not np.isfinite(p).all()), "is_synthetic": is_synthetic})
    return pd.DataFrame(rows)
