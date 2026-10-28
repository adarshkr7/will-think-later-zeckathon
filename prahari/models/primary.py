"""Fixed-weight primary score. No Indian labels are accepted by this API."""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd
from scipy.special import expit, logit

from prahari.features.common import MissingInput, Value, evaluate, number
from prahari.models.prior_shift import prior_shift


def soft_contributions(values: Mapping, settings: dict, arena: str) -> dict[str, float]:
    """Fixed Phase 4 override weights; upgrades do not cancel observed red flags."""
    enabled = settings["arena_u_soft"] if arena == "U" else settings["soft_weights"].keys()
    result = {}
    for name in enabled:
        if name == "pledge_jump":
            value = float(number(values, "pledge_delta_4q") > settings["pledge_jump_pp"])
        elif name == "audit_default_or_going_concern":
            flags = [values.get(key, np.nan) for key in ("going_concern_flag", "caro_default_flag")]
            if any(pd.notna(flag) and flag == 1 for flag in flags):
                value = 1.0
            elif all(pd.notna(flag) and flag == 0 for flag in flags):
                value = 0.0
            else:
                raise MissingInput("missing:audit_default_or_going_concern")
        else:
            value = number(values, name)
            value = max(0, value) if name == "rating_notch_delta_4q" else value
            if name != "rating_notch_delta_4q" and value not in (0, 1):
                raise MissingInput("invalid_binary:" + name)
        result[name] = settings["soft_weights"][name] * value
    return result


def primary_logit(values: Mapping, hdm_probability: float, training_prior: float,
                  horizon: str, settings: dict, arena: str) -> tuple[Value, dict[str, float]]:
    """PROJECT_IDEA §8b/Phase 4 override: prior-shifted HDM + CHS + fixed soft.

    NBFC risk ranks are not called probabilities without a declared logit scale
    and verified prior. Missing priors/overlays remain unavailable; no panel
    prevalence, labels or fitted Indian calibration enter this calculation.
    """
    contributions = {}
    def calculate() -> float:
        prior = number(settings["priors"], horizon)
        if not 0 < prior < 1 or not settings.get("prior_source"):
            raise MissingInput("unverified_indian_prior")
        financial = number(values, "is_financial")
        if financial == 1:
            contributions["baseline_prior"] = float(logit(prior))
            contributions["nbfc_score"] = number(settings, "nbfc_logit_scale") * (number(values, "nbfc_score") - settings["nbfc_center"])
        elif financial == 0:
            if not np.isfinite(hdm_probability):
                raise MissingInput("insufficient_hdm_inputs_or_cross_section")
            shifted = prior_shift(hdm_probability, training_prior, prior).item()
            contributions["hdm_logit"] = settings["hdm_weight"] * float(logit(np.clip(shifted, settings["probability_epsilon"], 1 - settings["probability_epsilon"])))
        else:
            raise MissingInput("invalid_financial_classification")
        contributions["chs_standardized"] = settings["chs_weight"] * number(values, "chs_standardized")
        contributions.update(soft_contributions(values, settings, arena))
        return sum(contributions.values())
    value = evaluate(calculate)
    return value, contributions if not value.reason else {}


def score_primary(features: pd.DataFrame, probabilities: Mapping[str, np.ndarray], priors: Mapping[str, float], settings: dict, arena: str) -> pd.DataFrame:
    from prahari.features.common import require_snapshot
    require_snapshot(features)
    if "target" in features or any(name.startswith("y_") or name == "event_date" for name in features):
        raise ValueError("Indian outcomes must never enter primary scoring")
    result = features[[name for name in ("entity_id", "name", "symbols", "sector", "is_financial", "scoring_date", "max_source_date", "is_synthetic") if name in features]].copy()
    records = features.to_dict(orient="records")
    cutoff = pd.to_datetime(features.attrs["as_of"], utc=True)
    def score(row: Mapping, probability: float, horizon: str) -> Value:
        if pd.isna(row.get("max_source_date")):
            return Value(np.nan, "no_public_source_before_cutoff")
        if pd.isna(row.get("financial_period_end")) or pd.to_datetime(row["financial_period_end"], utc=True) < cutoff - pd.DateOffset(months=settings["maximum_financial_age_months"]):
            return Value(np.nan, "missing_or_stale_financial_statement")
        return primary_logit(row, probability, priors[horizon], horizon, settings, arena)[0]
    for horizon, probabilities_h in probabilities.items():
        if len(probabilities_h) != len(features):
            raise ValueError("HDM probability rows do not match features")
        values = [score(row, probability, horizon)
                  for row, probability in zip(records, probabilities_h, strict=True)]
        result["logit_" + horizon] = [value.value for value in values]
        result["pd_" + horizon] = expit(result["logit_" + horizon])
        result["score_reason_" + horizon] = [value.reason for value in values]
    result["arena"] = arena
    result["needs_verification"] = result[["pd_4q", "pd_8q"]].isna().any(axis=1).astype(int)
    return result
