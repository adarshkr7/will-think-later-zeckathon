"""Frozen-model scoring orchestration; accepts features, never Indian labels."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import logit

from prahari.models.hdm import predict_india
from prahari.models.primary import score_primary
from prahari.models.primary import soft_contributions
from prahari.models.prior_shift import prior_shift
from prahari.features.common import MissingInput


def score_snapshot(features: pd.DataFrame, models: dict, settings: dict, arena: str) -> tuple[pd.DataFrame, dict]:
    probabilities, priors, designs = {}, {}, {}
    nonfinancial = features.is_financial.eq(0)
    for horizon, model in models.items():
        raw = features.reindex(columns=model.columns).apply(pd.to_numeric, errors="raise")
        # Financial-firm inputs cannot enter the foreign corporate HDM ranks.
        raw = raw.where(nonfinancial, np.nan)
        probability, design = predict_india(model, raw, settings["primary"])
        probabilities[horizon], priors[horizon], designs[horizon] = probability, model.training_prior, design
    scores = score_primary(features, probabilities, priors, settings["primary"], arena)
    for horizon, probability in probabilities.items():
        new_prior = settings["primary"]["priors"].get(horizon)
        scores["hdm_logit_" + horizon] = logit(np.clip(prior_shift(probability, priors[horizon], new_prior),
            settings["primary"]["probability_epsilon"], 1-settings["primary"]["probability_epsilon"])) if new_prior is not None else np.nan
    overlays = []
    for row in features.to_dict(orient="records"):
        try:
            overlays.append(sum(soft_contributions(row, settings["primary"], arena).values()))
        except MissingInput:
            overlays.append(np.nan)
    scores["soft_overlay"] = overlays
    for field in ("chs_standardized", "z_classic", "z_em", "m_score", "f_score", "rating_notch_delta_4q", "drawdown_52w"):
        scores[field] = features[field] if field in features else np.nan
    flags = features.reindex(columns=["caro_default_flag", "rating_default_grade"])
    scores["hard_trigger"] = np.where(flags.eq(1).any(axis=1), 1, np.where(flags.eq(0).all(axis=1), 0, np.nan))
    scores.attrs.update(features.attrs)
    return scores, designs
