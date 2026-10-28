"""Hard budget, deterministic ties and distinct containment classification."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from prahari.policy.threshold import bayes_threshold


def build_watchlist(scores: pd.DataFrame, settings: dict, *, probability: str = "pd_4q") -> pd.DataFrame:
    """Expected-cost ordering subject to floor(alert_frac*N); hard triggers first.

    No unscored borrower fills a spare slot without an observed hard trigger.
    The denominator is the entire declared universe, including missing scores.
    """
    if scores.entity_id.duplicated().any():
        raise ValueError("Watch-list universe contains duplicate entities")
    result = scores.copy()
    p = pd.to_numeric(result[probability], errors="raise")
    if ((p.dropna() < 0) | (p.dropna() > 1)).any():
        raise ValueError("Invalid default probabilities")
    hard = result["hard_trigger"].eq(1) if "hard_trigger" in result else pd.Series(False, index=result.index)
    result["observed_hard_trigger"] = hard.astype(int)
    limit = math.floor(settings["alert_frac"] * len(result))
    result = result.sort_values(["observed_hard_trigger", probability, "entity_id"], ascending=[False, False, True], na_position="last", kind="stable")
    eligible = result[probability].notna() | result.observed_hard_trigger.eq(1)
    result["rank"] = pd.Series(np.arange(1, len(result) + 1), index=result.index).where(eligible).astype("Int64")
    chosen = result.loc[eligible].head(limit).index
    result["deep_review"] = result.index.isin(chosen).astype(int)
    threshold = bayes_threshold(settings["cost_fn"], settings["cost_fp"])
    result["tier"] = "monitor"
    result.loc[result[probability].isna(), "tier"] = "unscored"
    result.loc[result[probability].ge(threshold) | result.observed_hard_trigger.eq(1), "tier"] = "containment"
    result.loc[result.deep_review.eq(1), "tier"] = "tier3"
    result.loc[result.deep_review.eq(1) & result[probability].ge(threshold), "tier"] = "tier2"
    result.loc[result.deep_review.eq(1) & (result[probability].ge(settings["tier1_pd"]) | result.observed_hard_trigger.eq(1)), "tier"] = "tier1"
    result["review_cap"] = limit
    if result.deep_review.sum() > limit:
        raise AssertionError("Deep-review cap exceeded")
    return result.reset_index(drop=True)
