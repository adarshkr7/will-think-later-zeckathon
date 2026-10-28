"""Nested benchmark CV. Selection and calibration stay inside outer folds."""

from __future__ import annotations

from dataclasses import dataclass
import logging

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from prahari.models.calibrate import ProbabilityCalibrator
from prahari.models.preprocess import FoldPreprocessor

LOG = logging.getLogger(__name__)


class FoldWeightedLGBM(LGBMClassifier):
    """Estimate neg/pos from the actual fit fold, never validation labels."""

    def __init__(self, *, fold_class_weight: bool = False, **kwargs: object) -> None:
        self.fold_class_weight = fold_class_weight
        super().__init__(**kwargs)

    def fit(self, X: object, y: object, **kwargs: object) -> FoldWeightedLGBM:
        labels = np.asarray(y)
        if self.fold_class_weight:
            positive = int(labels.sum())
            if not 0 < positive < len(labels):
                raise ValueError("Both classes needed for fold weighting")
            self.set_params(scale_pos_weight=(len(labels) - positive) / positive)
        return super().fit(X, y, **kwargs)


@dataclass
class FittedBenchmark:
    pipeline: Pipeline
    calibrator: ProbabilityCalibrator
    columns: list[str]
    training_prior: float
    best_params: dict
    fit_indices: tuple
    representation: str
    source: str
    transfer_preprocessor: FoldPreprocessor | None = None

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if list(X.columns) != self.columns:
            raise ValueError("Benchmark feature schema changed")
        return self.calibrator.predict(self.pipeline.predict_proba(X)[:, 1])

    def predict_transfer(self, X: pd.DataFrame) -> np.ndarray:
        if self.transfer_preprocessor is None or list(X.columns) != self.columns:
            raise ValueError("Target-country rank reference is not fitted or schema differs")
        ranked = self.transfer_preprocessor.transform(X)
        return self.calibrator.predict(self.pipeline.named_steps["model"].predict_proba(ranked)[:, 1])


@dataclass
class DevelopmentResult:
    model: FittedBenchmark
    probabilities: np.ndarray
    folds: list[dict]


def make_pipeline(settings: dict, seed: int, variant: str, *, monotone: list[int] | None = None) -> Pipeline:
    prep = FoldPreprocessor(**{k: settings["preprocessing"][k]
                               for k in ("lower_quantile", "upper_quantile", "correlation_threshold")},
                            rank=monotone is not None, prune=monotone is None)
    if variant == "logistic":
        estimator = LogisticRegression(**settings["models"]["logistic"], random_state=seed)
        return Pipeline([("preprocess", prep), ("scale", StandardScaler()), ("model", estimator)])
    if variant not in settings["models"]["imbalance_variants"]:
        raise ValueError(f"Unregistered imbalance variant: {variant}")
    options = {**settings["models"]["lightgbm"], "random_state": seed,
               "fold_class_weight": variant == "class_weight"}
    if monotone is not None:
        # Keep every HDM ratio in config order. Missingness indicators unconstrained.
        options["monotone_constraints"] = monotone + [0] * len(monotone)
    return Pipeline([("preprocess", prep), ("model", FoldWeightedLGBM(**options))])


def _folds(count: int, seed: int, y: np.ndarray) -> StratifiedKFold:
    if min(np.bincount(y.astype(int), minlength=2)) < count:
        raise ValueError("Too few positives/negatives for configured folds")
    return StratifiedKFold(n_splits=count, shuffle=True, random_state=seed)


def _search(pipeline: Pipeline, X: pd.DataFrame, y: np.ndarray, settings: dict, seed: int,
            variant: str) -> tuple[Pipeline, dict]:
    if variant == "logistic":
        fitted = clone(pipeline).fit(X, y)
        return fitted, {}
    search = GridSearchCV(pipeline, {f"model__{key}": value for key, value in settings["models"]["grid"].items()},
                          scoring="average_precision", cv=_folds(settings["cv"]["inner_folds"], seed, y),
                          n_jobs=settings["cv"]["n_jobs"], error_score="raise", refit=True)
    search.fit(X, y)
    return search.best_estimator_, search.best_params_


def _calibrator(pipeline: Pipeline, X: pd.DataFrame, y: np.ndarray, settings: dict,
                seed: int) -> ProbabilityCalibrator:
    oof = cross_val_predict(clone(pipeline), X, y,
                           cv=_folds(settings["cv"]["calibration_folds"], seed, y),
                           method="predict_proba", n_jobs=settings["cv"]["n_jobs"])[:, 1]
    return ProbabilityCalibrator(settings["calibration"]["isotonic_min_positives"], seed).fit(oof, y)


def nested_development(X: pd.DataFrame, y: np.ndarray, settings: dict, seed: int, variant: str,
                       *, source: str, monotone: list[int] | None = None) -> DevelopmentResult:
    """Each outer validation row is excluded from tuning and calibration.

    Calibration scores use cross-fitted models inside the outer training data.
    Hyperparameters for those models are selected on that outer training data;
    only outer-fold metrics constitute the unbiased development estimate.
    """
    y = np.asarray(y, dtype=int)
    template = make_pipeline(settings, seed, variant, monotone=monotone)
    probabilities = np.full(len(y), np.nan)
    audits = []
    for fold, (train, valid) in enumerate(_folds(settings["cv"]["outer_folds"], seed, y).split(X, y)):
        pipeline, params = _search(template, X.iloc[train], y[train], settings, seed, variant)
        calibrator = _calibrator(pipeline, X.iloc[train], y[train], settings, seed)
        probabilities[valid] = calibrator.predict(pipeline.predict_proba(X.iloc[valid])[:, 1])
        fitted_indices = set(pipeline.named_steps["preprocess"].fit_indices_)
        if fitted_indices.intersection(X.index[valid]):
            raise AssertionError("Preprocessor saw outer validation indices")
        audits.append({"fold": fold, "train_rows": len(train), "validation_rows": len(valid),
                       "best_params": params, "calibration": calibrator.kind_,
                       "empty_features": list(pipeline.named_steps["preprocess"].empty_columns_),
                       "fit_validation_overlap": 0})
        LOG.info("%s %s outer_fold=%s complete; rows=%s dates_imputed=0 missing_features=%s",
                 source, variant, fold + 1, len(train), audits[-1]["empty_features"])
    pipeline, params = _search(template, X, y, settings, seed, variant)
    calibrator = _calibrator(pipeline, X, y, settings, seed)
    model = FittedBenchmark(pipeline, calibrator, list(X.columns), float(y.mean()), params,
                            tuple(X.index), "harmonized" if monotone is not None else "full", source)
    return DevelopmentResult(model, probabilities, audits)
