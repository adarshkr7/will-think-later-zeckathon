"""Calibration fitted only on out-of-fold benchmark predictions."""

from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


class ProbabilityCalibrator:
    def __init__(self, min_positives: int, seed: int) -> None:
        self.min_positives = min_positives
        self.seed = seed

    def fit(self, scores: np.ndarray, y: np.ndarray) -> ProbabilityCalibrator:
        scores = np.asarray(scores, dtype=float)
        y = np.asarray(y)
        if not np.isfinite(scores).all() or len(np.unique(y)) != 2:
            raise ValueError("Calibration needs finite scores and both classes")
        self.kind_ = "isotonic" if int(y.sum()) >= self.min_positives else "platt"
        if self.kind_ == "isotonic":
            self.model_ = IsotonicRegression(out_of_bounds="clip").fit(scores, y)
        else:
            self.model_ = LogisticRegression(random_state=self.seed).fit(scores.reshape(-1, 1), y)
        return self

    def predict(self, scores: np.ndarray) -> np.ndarray:
        scores = np.asarray(scores, dtype=float)
        if self.kind_ == "isotonic":
            return self.model_.predict(scores)
        return self.model_.predict_proba(scores.reshape(-1, 1))[:, 1]
