"""Transparent PR metrics, uncertainty and cost descriptions."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import average_precision_score, brier_score_loss, precision_recall_curve, roc_auc_score, auc

from prahari.policy.threshold import bayes_threshold


def validate_predictions(y: np.ndarray, p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    labels, scores = np.asarray(y), np.asarray(p, dtype=float)
    if labels.ndim != 1 or scores.shape != labels.shape or len(labels) == 0:
        raise ValueError("Non-empty matching one-dimensional predictions required")
    if not np.isin(labels, [0, 1]).all() or len(np.unique(labels)) != 2:
        raise ValueError("Both binary classes required for benchmark evaluation")
    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("Invalid probabilities")
    return labels.astype(int), scores


def calibration_table(y: np.ndarray, p: np.ndarray, bins: int) -> pd.DataFrame:
    y, p = validate_predictions(y, p)
    ids = np.minimum((p * bins).astype(int), bins - 1)
    rows = []
    for index in range(bins):
        mask = ids == index
        rows.append({"bin": index, "count": int(mask.sum()),
                     "mean_probability": float(p[mask].mean()) if mask.any() else None,
                     "observed_rate": float(y[mask].mean()) if mask.any() else None,
                     "is_synthetic": 0})
    return pd.DataFrame(rows)


def realised_cost(y: np.ndarray, selected: np.ndarray, policy: dict) -> float:
    return float(policy["cost_fn"] * ((y == 1) & ~selected).sum()
                 + policy["cost_fp"] * ((y == 0) & selected).sum())


def wilson_interval(hits: int, total: int, confidence: float) -> tuple[float, float]:
    """Wilson (1927), JASA 22:209-212, score interval for a binomial share."""
    if total == 0:
        return float("nan"), float("nan")
    if not 0 <= hits <= total:
        raise ValueError("Invalid hit count")
    z = norm.ppf((1 + confidence) / 2)
    p = hits / total
    denominator = 1 + z*z / total
    centre = (p + z*z / (2*total)) / denominator
    radius = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / denominator
    return float(centre - radius), float(centre + radius)


def benchmark_metrics(y: np.ndarray, p: np.ndarray, settings: dict, policy: dict, seed: int) -> dict:
    """PR-AUC means average precision; trapezoidal PR area is also explicit.

    Ordinary row bootstrap (not model-refitting), two-class draws only. The
    interval excludes model-selection uncertainty and cross-firm dependence.
    Final threshold scans describe results; they must never tune the policy.
    """
    y, p = validate_predictions(y, p)
    generator = np.random.default_rng(seed)
    areas = []
    for _ in range(settings["bootstrap_resamples"]):
        positions = generator.integers(0, len(y), len(y))
        if len(np.unique(y[positions])) == 2:
            areas.append(average_precision_score(y[positions], p[positions]))
    if not areas:
        raise ValueError("No valid bootstrap resamples")
    alpha = (1 - settings["confidence"]) / 2
    lower, upper = np.quantile(areas, [alpha, 1-alpha])
    capacity = math.floor(policy["alert_frac"] * len(y))
    order = np.argsort(-p, kind="stable")[:capacity]
    selected = np.zeros(len(y), dtype=bool)
    selected[order] = True
    true_positives = int(y[order].sum())
    tau = bayes_threshold(policy["cost_fn"], policy["cost_fp"])
    grid = policy["threshold_grid"]
    thresholds = np.linspace(grid["start"], grid["stop"], grid["count"])
    costs = np.asarray([realised_cost(y, p >= threshold, policy) for threshold in thresholds])
    calibration = calibration_table(y, p, settings["ece_bins"]).dropna()
    ece = (calibration["count"] * (calibration["mean_probability"] - calibration["observed_rate"]).abs()).sum() / len(y)
    precision, recall, _ = precision_recall_curve(y, p)
    return {"n": len(y), "positives": int(y.sum()), "base_rate": float(y.mean()),
            "pr_auc": float(average_precision_score(y, p)), "pr_auc_ci_low": float(lower),
            "pr_auc_ci_high": float(upper), "pr_auc_definition": "average_precision",
            "trapezoid_pr_auc": float(auc(recall, precision)), "roc_auc": float(roc_auc_score(y, p)),
            "brier": float(brier_score_loss(y, p)), "ece": float(ece),
            "capacity": capacity, "recall_at_cap": true_positives / int(y.sum()),
            "precision_at_cap": true_positives / capacity if capacity else None,
            "tau_star": tau, "cost_at_tau_star_uncapped": realised_cost(y, p >= tau, policy),
            "cost_at_cap": realised_cost(y, selected, policy),
            "descriptive_tau_grid_min": float(thresholds[costs.argmin()]),
            "descriptive_grid_min_cost_uncapped": float(costs.min()),
            "bootstrap_valid_resamples": len(areas), "is_synthetic": 0}
