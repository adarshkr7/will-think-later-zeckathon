"""Dated sibling stress, computed once from label-free base scores."""

import numpy as np
import pandas as pd

from prahari.features.common import require_snapshot


def group_features(states: pd.DataFrame, membership: pd.DataFrame, quantile: float) -> pd.DataFrame:
    """Worst observed sibling state; never read retrospective default labels.

    Positive dated hard triggers suffice to establish stress. A negative state
    requires a complete sourced roster and complete base-score coverage. The
    focal entity is excluded, and base probabilities precede this overlay so
    there is no recursive same-quarter amplification.
    """
    require_snapshot(states)
    require_snapshot(membership)
    if states.attrs["as_of"] != membership.attrs["as_of"] or not 0 < quantile < 1:
        raise ValueError("Group context cutoff/quantile mismatch")
    current = membership.sort_values(["period_end", "public_date"]).drop_duplicates("entity_id", keep="last")
    scores = states.set_index("entity_id")
    complete_scores = states.pd_4q.notna().all() and not states.empty
    threshold = states.pd_4q.quantile(quantile) if complete_scores else np.nan
    rows = []
    for state in states.itertuples():
        own = current.loc[current.entity_id.eq(state.entity_id)]
        value, reason = np.nan, "group_membership_unknown"
        dates = [state.max_source_date]
        taint = int(state.is_synthetic)
        if not own.empty:
            roster = current.loc[current.group_id.eq(own.iloc[0].group_id)]
            others = roster.loc[roster.entity_id.ne(state.entity_id)]
            dates.append(roster.max_source_date.max())
            taint |= int(roster.is_synthetic.eq(1).any())
            visible = scores.reindex(others.entity_id)
            if not visible.empty:
                dates.append(visible.max_source_date.max())
                taint |= int(visible.is_synthetic.eq(1).any())
            positive = visible.hard_trigger.eq(1).any() or (complete_scores and visible.pd_4q.ge(threshold).any())
            if positive:
                value, reason = 1., ""
            elif roster.membership_complete.eq(1).all() and (others.empty or (complete_scores and visible.pd_4q.notna().all() and visible.hard_trigger.notna().all())):
                value, reason = 0., ""
            else:
                reason = "incomplete_group_roster_or_sibling_scores"
            if complete_scores:
                dates.append(states.max_source_date.max())
                taint |= int(states.is_synthetic.eq(1).any())
        rows.append({"entity_id": state.entity_id, "group_stress": value, "group_stress__reason": reason,
                     "max_source_date": max((day for day in dates if pd.notna(day)), default=pd.NaT), "is_synthetic": taint})
    result = pd.DataFrame(rows)
    result.attrs.update(states.attrs)
    return result
