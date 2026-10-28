"""Operational metrics with sourced non-default windows and explicit censoring."""

import numpy as np
import pandas as pd


def verified_window_labels(predictions, events, survival, horizon, event_field="event_date"):
    """Only reviewed event or reviewed survivor coverage can determine an outcome.

    A background firm absent from events is not silently labelled a survivor.
    A verified default establishes pre-event non-default windows, not coverage
    after the first default. Post-default and uncovered rows remain unknown.
    """
    known = events.loc[events.needs_verification.eq(0)].set_index("entity_id")[event_field]
    survivors = survival.loc[survival.needs_verification.eq(0)]
    values = []
    for row in predictions.itertuples():
        start = pd.to_datetime(row.scoring_date, utc=True)
        end = start + pd.DateOffset(months=3*horizon)
        event = pd.to_datetime(known.get(row.entity_id), utc=True)
        label = np.nan
        if pd.notna(event) and start < event:
            label = float(event <= end)
        windows = survivors.loc[survivors.entity_id.eq(row.entity_id)]
        for window in windows.itertuples():
            if pd.to_datetime(window.nondefault_start, utc=True) <= start and pd.to_datetime(window.nondefault_through, utc=True) >= end:
                if label == 1:
                    raise ValueError("Survival evidence conflicts with a verified event")
                label = 0.0
        values.append(label)
    return pd.Series(values, index=predictions.index)


def operating_metrics(predictions, events, survival, peers, policy, arena):
    rows = []
    stressed = set(peers.loc[peers.needs_verification.eq(0) & peers.is_stressed_survivor.eq(1), "entity_id"])
    for field in ("event_date", "cirp_admission_date"):
        table = predictions.copy()
        table["label"] = verified_window_labels(table, events, survival, 4, field)
        for day, group in table.groupby("scoring_date", sort=True):
            selected = group.deep_review.eq(1)
            known = group.label.notna()
            negatives = group.label.eq(0)
            hard_negatives = negatives & group.entity_id.isin(stressed)
            fn = (group.label.eq(1) & ~selected).sum()
            fp = (negatives & selected).sum()
            precision = group.loc[selected, "label"].mean() if selected.any() and group.loc[selected, "label"].notna().all() else np.nan
            rows.append({"arena": arena, "event_definition": field, "scoring_date": day, "known_outcomes": int(known.sum()),
                         "unknown_outcomes": int((~known).sum()), "precision": precision,
                         "false_alarm_rate_known_survivors": fp / negatives.sum() if negatives.any() else np.nan,
                         "false_alarm_rate_stressed_survivors": (selected & hard_negatives).sum() / hard_negatives.sum() if hard_negatives.any() else np.nan,
                         "realized_cost": float(policy["cost_fn"]*fn + policy["cost_fp"]*fp) if known.all() else np.nan,
                         "needs_verification": int(not known.all()), "is_synthetic": int(group.is_synthetic.eq(1).any())})
        for case in events.loc[events.needs_verification.eq(0)].to_dict(orient="records"):
            event = pd.to_datetime(case.get(field), utc=True)
            if pd.isna(event):
                continue
            history = predictions.loc[predictions.entity_id.eq(case["entity_id"])].copy()
            history["date"] = pd.to_datetime(history.scoring_date, utc=True)
            window = history.loc[history.date.ge(event-pd.DateOffset(months=24)) & history.date.le(event-pd.DateOffset(months=12))]
            prior_flags = history.loc[history.date.lt(event) & history.deep_review.eq(1)]
            first = prior_flags.date.min()
            lead = ((event.year-first.year)*12+event.month-first.month)/3 if pd.notna(first) else np.nan
            rows.append({"arena": arena, "entity_id": case["entity_id"], "event_definition": field,
                "ever_flagged_8q_to_4q": int(window.deep_review.eq(1).any()) if not window.empty else np.nan,
                "first_flag_lead_quarters": lead, "first_flag_date": first,
                "needs_verification": int(window.empty or window.pd_4q.isna().any()), "is_synthetic": int(case["is_synthetic"])})
    previous = None
    for day, group in predictions.groupby("scoring_date", sort=True):
        selected = set(group.loc[group.deep_review.eq(1), "entity_id"])
        union = selected | previous if previous is not None else set()
        rows.append({"arena": arena, "event_definition": "watchlist_turnover", "scoring_date": day,
                     "turnover_jaccard": len(selected ^ previous) / len(union) if previous is not None and union else np.nan,
                     "needs_verification": int(group.pd_4q.isna().any()), "is_synthetic": int(group.is_synthetic.eq(1).any())})
        previous = selected
    return pd.DataFrame(rows)
