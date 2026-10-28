"""Counterfactual budget/cost summaries; no alternative operational list is saved."""

import numpy as np
import pandas as pd

from prahari.policy.cost import expected_cost, realized_cost


def policy_scenarios(scores: pd.DataFrame, labels: pd.Series, policy: dict, settings: dict) -> pd.DataFrame:
    if scores.entity_id.duplicated().any():
        raise ValueError("Scenario universe must contain distinct entities")
    frame = scores.copy()
    frame["label"] = labels
    frame["hard_priority"] = frame.hard_trigger.eq(1).astype(int)
    ordered = frame.sort_values(["hard_priority", "pd_4q", "entity_id"], ascending=[False, False, True], na_position="last", kind="stable")
    rows = []
    for slots in settings["review_slots"]:
        if slots < 0:
            raise ValueError("Scenario slots cannot be negative")
        eligible = ordered.pd_4q.notna() | ordered.hard_priority.eq(1)
        selected = eligible & (eligible.cumsum() <= slots)
        for ratio in settings["false_negative_cost_ratios"]:
            if ratio <= 0:
                raise ValueError("Scenario cost ratios must be positive")
            costs = {**policy, "cost_fn": ratio*policy["cost_fp"]}
            positives = ordered.label.eq(1)
            rows.append({"review_slots": slots, "selected_count": int(selected.sum()), "cost_ratio": ratio,
                "expected_cost": expected_cost(ordered.pd_4q.to_numpy(), selected.to_numpy(), costs),
                "realized_cost": realized_cost(ordered.label.to_numpy(), selected.to_numpy(), costs),
                "recall_known_outcomes": int((positives & selected).sum())/positives.sum() if positives.any() else np.nan,
                "is_counterfactual_budget": 1, "needs_verification": int(ordered.label.isna().any() or ordered.pd_4q.isna().any()),
                "is_synthetic": int(frame.is_synthetic.eq(1).any())})
    return pd.DataFrame(rows)
