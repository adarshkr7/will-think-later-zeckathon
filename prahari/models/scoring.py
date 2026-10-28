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


def score_snapshot(features: pd.DataFrame, models: dict, settings: dict, arena: str, *, groups=None) -> tuple[pd.DataFrame, dict]:
    probabilities, priors, designs = {}, {}, {}
    nonfinancial = features.is_financial.eq(0)
    for horizon, model in models.items():
        raw = features.reindex(columns=model.columns).apply(pd.to_numeric, errors="raise")
        # Financial-firm inputs cannot enter the foreign corporate HDM ranks.
        raw = raw.where(nonfinancial, np.nan)
        probability, design = predict_india(model, raw, settings["primary"])
        probabilities[horizon], priors[horizon], designs[horizon] = probability, model.training_prior, design
    scores = score_primary(features, probabilities, priors, {**settings["primary"], "group_enabled": False}, arena)
    flags = features.reindex(columns=["caro_default_flag", "rating_default_grade"])
    hard = np.where(flags.eq(1).any(axis=1), 1, np.where(flags.eq(0).all(axis=1), 0, np.nan))
    scores["hard_trigger"] = hard
    scores.attrs.update(features.attrs)
    if settings["primary"].get("group_enabled") and arena in settings["primary"]["group_arenas"]:
        enriched = features.copy()
        if groups is not None:
            from prahari.features.group import group_features
            context = group_features(scores, groups, settings["primary"]["group_pd_quantile"]).set_index("entity_id")
            enriched["group_stress"] = enriched.entity_id.map(context.group_stress)
            dates = pd.to_datetime(enriched.entity_id.map(context.max_source_date), utc=True)
            enriched["max_source_date"] = pd.concat([enriched.max_source_date, dates], axis=1).max(axis=1)
            enriched["is_synthetic"] = (enriched.is_synthetic.eq(1) | enriched.entity_id.map(context.is_synthetic).eq(1)).astype(int)
        elif "group_stress" not in enriched:
            enriched["group_stress"] = np.nan
        scores = score_primary(enriched, probabilities, priors, settings["primary"], arena)
        scores["group_stress"] = enriched.group_stress
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
    scores["hard_trigger"] = hard
    if features.is_synthetic.eq(1).any() or (groups is not None and groups.is_synthetic.eq(1).any()):
        scores["is_synthetic"] = 1
    scores.attrs.update(features.attrs)
    return scores, designs
