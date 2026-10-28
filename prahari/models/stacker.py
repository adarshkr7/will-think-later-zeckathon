"""Ablation-only bounded logistic stacking with nested group-out calibration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

from prahari.models.calibrate import ProbabilityCalibrator


@dataclass
class BoundedLogistic:
    signs: list[int]
    c: float
    max_iter: int

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "BoundedLogistic":
        if len(self.signs) != X.shape[1] or len(np.unique(y)) != 2:
            raise ValueError("Ablation fit needs known signs and both classes")
        self.columns_ = list(X)
        self.median_ = X.median()
        if self.median_.isna().any():
            raise ValueError("Ablation feature lacks training evidence")
        filled = X.fillna(self.median_)
        self.center_ = filled.mean()
        self.scale_ = filled.std(ddof=0).replace(0, 1)
        design = ((filled - self.center_) / self.scale_).to_numpy(dtype=float)
        labels = np.asarray(y, dtype=float)
        def objective(parameters):
            margin = parameters[0] + design @ parameters[1:]
            loss = np.logaddexp(0, margin).sum() - labels @ margin + .5 * (parameters[1:] @ parameters[1:]) / self.c
            residual = expit(margin) - labels
            gradient = np.r_[residual.sum(), design.T @ residual + parameters[1:] / self.c]
            return loss, gradient
        bounds = [(None, None)] + [(0, None) if sign > 0 else ((None, 0) if sign < 0 else (None, None)) for sign in self.signs]
        fitted = minimize(objective, np.zeros(X.shape[1] + 1), jac=True, bounds=bounds, method="L-BFGS-B", options={"maxiter": self.max_iter})
        if not fitted.success:
            raise ValueError("Bounded ablation fit did not converge")
        self.intercept_, self.coef_ = fitted.x[0], fitted.x[1:]
        self.fit_indices_ = tuple(X.index)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if list(X) != self.columns_:
            raise ValueError("Ablation feature schema changed")
        design = ((X.fillna(self.median_) - self.center_) / self.scale_).to_numpy(dtype=float)
        return expit(self.intercept_ + design @ self.coef_)


def group_oof_stacker(X: pd.DataFrame, y: np.ndarray, groups: np.ndarray, signs: list[int], settings: dict, seed: int, *, train_eligible=None) -> tuple[np.ndarray, list[dict]]:
    """Every outer prediction excludes its whole case-connected component.

    Inner leave-group-out predictions calibrate only outer-training labels.
    Neither outer labels nor any primary-model component is fitted here.
    """
    labels, group = np.asarray(y), np.asarray(groups)
    eligible = np.ones(len(X), dtype=bool) if train_eligible is None else np.asarray(train_eligible, dtype=bool)
    eligible = eligible & np.isin(labels, [0, 1])
    unique = np.unique(group)
    if len(unique) < settings["minimum_case_groups"]:
        raise ValueError("Too few independent case groups for the ablation-only stacker")
    probabilities = np.full(len(X), np.nan)
    audits = []
    def model():
        return BoundedLogistic(signs, settings["logistic_c"], settings["max_iter"])
    for held in unique:
        train, test = (group != held) & eligible, group == held
        inner = np.full(len(X), np.nan)
        try:
            for validation_group in unique[unique != held]:
                fit = train & (group != validation_group)
                validation = train & (group == validation_group)
                if not validation.any():
                    continue
                fitted = model().fit(X.loc[fit], labels[fit])
                inner[validation] = fitted.predict(X.loc[validation])
            if not np.isfinite(inner[train]).all():
                raise ValueError("Incomplete nested calibration predictions")
            calibrator = ProbabilityCalibrator(settings["min_calibration_positives"], seed).fit(inner[train], labels[train])
            fitted = model().fit(X.loc[train], labels[train])
            probabilities[test] = calibrator.predict(fitted.predict(X.loc[test]))
            status = "out_of_fold"
        except ValueError as exc:
            status = "not_fit:" + str(exc)
        audits.append({"held_group": str(held), "fit_groups": [str(value) for value in unique[unique != held]],
                       "fit_rows": int(train.sum()), "test_rows": int(test.sum()), "status": status})
    return probabilities, audits
