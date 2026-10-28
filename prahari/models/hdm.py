"""Apply a frozen Polish HDM to unlabelled Indian cross-section ranks."""

from __future__ import annotations

import numpy as np
import pandas as pd

from prahari.models.benchmark import FittedBenchmark


def india_design(model: FittedBenchmark, raw: pd.DataFrame, minimum_cross_section: int) -> pd.DataFrame:
    """Quarter-local ECDF ranks, with missingness indicators preserved.

    India raw ratios never pass through Polish raw-value winsor cutoffs or its
    ECDF a second time. Only missing ranks use the frozen Polish median's rank;
    this is the predeclared training-fold imputation, not a financial zero.
    """
    if list(raw.columns) != model.columns:
        raise ValueError("HDM canonical feature schema/order changed")
    prep = model.pipeline.named_steps["preprocess"]
    if not prep.rank or prep.prune:
        raise ValueError("India transfer requires an unpruned harmonized rank model")
    ranks = pd.DataFrame(index=raw.index)
    raw = raw.replace([np.inf, -np.inf], np.nan)
    missing = raw.isna().astype(float)
    for column in raw:
        clean = pd.to_numeric(raw[column], errors="raise").replace([np.inf, -np.inf], np.nan)
        count = clean.notna().sum()
        if count < minimum_cross_section:
            ranks[column] = np.nan
            continue
        ranks[column] = (clean.rank(method="average") - .5) / count
        reference = prep.references_[column]
        median = prep.medians_[column]
        if len(reference) and np.isfinite(median):
            fill = (np.searchsorted(reference, median, side="left") + np.searchsorted(reference, median, side="right")) / (2 * len(reference))
            ranks[column] = ranks[column].fillna(fill)
    return pd.concat([ranks, missing.rename(columns=lambda name: name + "__missing")], axis=1)


def predict_india(model: FittedBenchmark, raw: pd.DataFrame, settings: dict) -> tuple[np.ndarray, pd.DataFrame]:
    design = india_design(model, raw, settings["minimum_hdm_cross_section"])
    eligible = raw.replace([np.inf, -np.inf], np.nan).notna().sum(axis=1).ge(settings["minimum_hdm_observed"]) & design.iloc[:, :len(model.columns)].notna().all(axis=1)
    probabilities = np.full(len(raw), np.nan)
    if eligible.any():
        scores = model.pipeline.named_steps["model"].predict_proba(design.loc[eligible])[:, 1]
        probabilities[eligible.to_numpy()] = model.calibrator.predict(scores)
    return probabilities, design
