"""Exact score reconciliation, with calibration treatment stated explicitly."""

from __future__ import annotations

from collections.abc import Callable, Mapping

import numpy as np
from scipy.special import expit, logit

from prahari.models.prior_shift import prior_shift


def calibrated_margin_allocation(raw: np.ndarray, calibrator, prior_old: float, prior_new: float,
                                epsilon: float, step: float) -> tuple[np.ndarray, np.ndarray]:
    """Rescale native TreeSHAP margins to exactly reconcile calibrated log-odds.

    Lundberg & Lee (2017), TreeSHAP on the raw margin; Saerens et al. (2002)
    prior odds. This is a path-proportional allocation of a nonlinear calibrated
    margin, NOT Shapley values of the calibrated probability function. Opposing
    margin contributions use the local finite-difference slope at zero net sum.
    """
    values = np.asarray(raw, dtype=float)
    if values.ndim != 2 or values.shape[1] < 2 or not np.isfinite(values).all() or step <= 0:
        raise ValueError("Finite feature contributions plus an intercept are required")
    def mapping(margin: np.ndarray) -> np.ndarray:
        p = calibrator.predict(expit(margin))
        return logit(np.clip(prior_shift(p, prior_old, prior_new), epsilon, 1 - epsilon))
    base = values[:, -1]
    delta = values[:, :-1].sum(axis=1)
    baseline, final = mapping(base), mapping(base + delta)
    slope = np.empty(len(base))
    nonzero = np.abs(delta) > np.finfo(float).eps
    slope[nonzero] = (final[nonzero] - baseline[nonzero]) / delta[nonzero]
    slope[~nonzero] = (mapping(base[~nonzero] + step) - mapping(base[~nonzero] - step)) / (2 * step) if (~nonzero).any() else []
    allocated = values[:, :-1] * slope[:, None]
    if not np.allclose(baseline + allocated.sum(axis=1), final, atol=epsilon, rtol=0):
        raise AssertionError("Calibrated margin reconciliation failed")
    return baseline, allocated


def reconcile(intercept: float, contributions: Mapping[str, float], final_logit: float, tolerance: float) -> None:
    total = intercept + sum(contributions.values())
    if not np.isfinite(total) or not np.isfinite(final_logit) or abs(total - final_logit) > tolerance:
        raise AssertionError("Attributions do not sum to the final logit")


def marginal_pd_points(final_logit: float, contributions: Mapping[str, float]) -> dict[str, float]:
    """Exact single-driver removal effects; these effects are not additive in PD."""
    return {name: float((expit(final_logit) - expit(final_logit - value)) * 100) for name, value in contributions.items()}


def linear_chs_allocation(values: Mapping[str, float], settings: dict, center: float,
                          scale: float, weight: float) -> tuple[float, dict[str, float]]:
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("CHS standardization scale must be positive")
    terms = {name: weight * coefficient * values[name] / scale for name, coefficient in settings["weights"].items()}
    return weight * (settings["intercept"] - center) / scale, terms
