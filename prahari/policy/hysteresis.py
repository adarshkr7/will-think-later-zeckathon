"""Separate turnover experiment; never changes the registered primary ranking."""

import pandas as pd

from prahari.policy.threshold import bayes_threshold
from prahari.policy.watchlist import build_watchlist


def hysteresis_watchlist(scores: pd.DataFrame, previous_ids: set[str], policy: dict, settings: dict, *, probability: str = "pd_4q") -> pd.DataFrame:
    """Retain eligible previous names after hard triggers, under the same cap."""
    release = bayes_threshold(policy["cost_fn"], policy["cost_fp"])*settings["release_threshold_multiplier"]
    if not 0 < settings["release_threshold_multiplier"] <= 1:
        raise ValueError("Hysteresis release multiplier must lie in (0,1]")
    frame = scores.copy()
    frame["retained_priority"] = (frame.entity_id.isin(previous_ids) & frame[probability].ge(release)).astype(int)
    result = build_watchlist(frame, policy, probability=probability, priority_columns=("retained_priority",))
    result["experiment"] = "hysteresis_only_not_primary"
    return result
