"""Cloneable fold-local preprocessing with explicit fit-index audits."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted


class FoldPreprocessor(TransformerMixin, BaseEstimator):
    def __init__(self, lower_quantile: float, upper_quantile: float,
                 correlation_threshold: float, rank: bool = False, prune: bool = True) -> None:
        self.lower_quantile = lower_quantile
        self.upper_quantile = upper_quantile
        self.correlation_threshold = correlation_threshold
        self.rank = rank
        self.prune = prune

    def fit(self, X: pd.DataFrame, y: object = None) -> FoldPreprocessor:
        if not isinstance(X, pd.DataFrame) or not X.columns.is_unique:
            raise ValueError("Expected a DataFrame with unique feature columns")
        self.fit_indices_ = tuple(X.index)
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        clean = X.replace([np.inf, -np.inf], np.nan).astype(float)
        self.medians_ = clean.median()
        self.empty_columns_ = tuple(self.medians_.loc[self.medians_.isna()].index)
        filled = clean.fillna(self.medians_)
        self.lower_ = filled.quantile(self.lower_quantile)
        self.upper_ = filled.quantile(self.upper_quantile)
        bounded = filled.clip(self.lower_, self.upper_, axis=1)
        self.references_ = {c: np.sort(bounded[c].dropna().to_numpy()) for c in bounded}
        keep = []
        correlation = bounded.corr().abs()
        for column in bounded:
            if not self.prune or not keep or not correlation.loc[column, keep].gt(self.correlation_threshold).any():
                keep.append(column)
        self.kept_columns_ = tuple(keep)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        check_is_fitted(self, "medians_")
        if list(X.columns) != list(self.feature_names_in_):
            raise ValueError("Feature schema/order changed")
        clean = X.replace([np.inf, -np.inf], np.nan).astype(float)
        missing = clean.isna().astype(float)
        bounded = clean.fillna(self.medians_).clip(self.lower_, self.upper_, axis=1)
        if self.rank:
            for column in bounded:
                reference = self.references_[column]
                if len(reference):
                    values = bounded[column].to_numpy()
                    left = np.searchsorted(reference, values, side="left")
                    right = np.searchsorted(reference, values, side="right")
                    # Mid-distribution ranks; endpoints are valid at unseen tails.
                    bounded[column] = (left + right) / (2 * len(reference))
                    bounded.loc[bounded[column].index[~np.isfinite(values)], column] = np.nan
        values = bounded.loc[:, list(self.kept_columns_)]
        indicators = missing.rename(columns=lambda c: f"{c}__missing")
        return pd.concat([values, indicators], axis=1)

    def get_feature_names_out(self, input_features: object = None) -> np.ndarray:
        check_is_fitted(self, "medians_")
        return np.asarray([*self.kept_columns_, *(f"{c}__missing" for c in self.feature_names_in_)])
