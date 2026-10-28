"""Descriptive drift with bins fitted only on the reference cross-section."""

from __future__ import annotations

import numpy as np


def psi_from_counts(reference: np.ndarray, current: np.ndarray, smoothing: float) -> float:
    """PSI = sum((q-p)*log(q/p)); SAS Model Manager, Population Stability.

    Additive count smoothing is declared in config. This descriptive quantity
    is not called a significance test or evidence that a model remains valid.
    """
    left, right = np.asarray(reference, dtype=float), np.asarray(current, dtype=float)
    if left.ndim != 1 or right.shape != left.shape or smoothing < 0 or not np.isfinite(left).all() or not np.isfinite(right).all() or (left < 0).any() or (right < 0).any():
        raise ValueError("PSI needs matching nonnegative finite histogram counts")
    if left.sum() <= 0 or right.sum() <= 0:
        return float("nan")
    p = (left+smoothing)/(left.sum()+smoothing*len(left))
    q = (right+smoothing)/(right.sum()+smoothing*len(right))
    if (p <= 0).any() or (q <= 0).any():
        return float("nan")
    return float(np.sum((q-p)*np.log(q/p)))


def population_stability(reference: np.ndarray, current: np.ndarray, settings: dict) -> dict:
    left, right = np.asarray(reference, dtype=float), np.asarray(current, dtype=float)
    if left.ndim != 1 or right.ndim != 1:
        raise ValueError("One-dimensional drift samples required")
    clean_left, clean_right = left[np.isfinite(left)], right[np.isfinite(right)]
    result = {"reference_n": len(clean_left), "current_n": len(clean_right),
              "reference_missing_fraction": 1-len(clean_left)/len(left) if len(left) else np.nan,
              "current_missing_fraction": 1-len(clean_right)/len(right) if len(right) else np.nan,
              "psi": np.nan, "status": "insufficient_observations"}
    if min(len(clean_left), len(clean_right)) < settings["minimum_observations"]:
        return result
    if clean_left.min() == clean_left.max():
        value = clean_left[0]
        cuts = [np.nextafter(value, -np.inf), np.nextafter(value, np.inf)]
    else:
        cuts = np.unique(np.quantile(clean_left, np.linspace(0, 1, settings["bins"]+1)))[1:-1]
    edges = np.r_[-np.inf, cuts, np.inf]
    result.update(psi=psi_from_counts(np.histogram(clean_left, edges)[0], np.histogram(clean_right, edges)[0], settings["smoothing_count"]),
                  bins=len(edges)-1, status="descriptive_reference_bins_frozen")
    return result
