"""Indian evaluation only. Outcome labels are never returned to primary fitting."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import norm


def wilson_interval(successes: int, total: int, confidence: float) -> tuple[float, float]:
    """Wilson (1927), JASA 22:209–212, score interval for a binomial proportion."""
    if total <= 0:
        return float("nan"), float("nan")
    if not 0 <= successes <= total or not 0 < confidence < 1:
        raise ValueError("Invalid binomial interval inputs")
    z = norm.ppf((1 + confidence) / 2)
    rate = successes / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    half = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denominator
    return max(0, center - half), min(1, center + half)


def strict_lead_observations(predictions: pd.DataFrame, events: pd.DataFrame, lead_quarters: int,
                             *, event_field: str = "event_date", head: str | None = None) -> pd.DataFrame:
    """Latest completed scoring quarter no later than event minus the stated lead.

    Missing/unscored snapshots are recorded explicitly. They count as misses
    in an accepted end-to-end replay, rather than disappearing from recall.
    """
    rows = []
    for case in events.loc[events.needs_verification.eq(0)].to_dict(orient="records"):
        event = pd.to_datetime(case.get(event_field), utc=True)
        if pd.isna(event):
            continue
        target = event - pd.DateOffset(months=3 * lead_quarters)
        required_date = pd.offsets.QuarterEnd(startingMonth=3).rollback(target.normalize())
        history = predictions.loc[predictions.entity_id.eq(case["entity_id"]) & pd.to_datetime(predictions.scoring_date, utc=True).eq(required_date)]
        head_name = head or (f"{lead_quarters}q" if lead_quarters in (4, 8) else "4q")
        row = {"entity_id": case["entity_id"], "event_date": event, "lead_quarters": lead_quarters,
               "sector": case.get("sector"), "period": str(event.year), "target_date": target, "required_scoring_date": required_date,
               "hit": 0, "scored": 0, "status": "no_snapshot_at_required_lead", "scoring_date": pd.NaT,
               "is_synthetic": int(case["is_synthetic"] or predictions.is_synthetic.eq(1).any())}
        if not history.empty:
            selected = history.sort_values("scoring_date").iloc[-1]
            row.update(hit=int(selected.get(f"deep_review_{head_name}", selected.deep_review) == 1), scored=int(pd.notna(selected.get(f"pd_{head_name}"))),
                       status="scored" if pd.notna(selected.get(f"pd_{head_name}")) else "unscored_missing_inputs",
                       scoring_date=selected.scoring_date)
        rows.append(row)
    return pd.DataFrame(rows)


def recall_table(predictions: pd.DataFrame, events: pd.DataFrame, settings: dict, arena: str) -> pd.DataFrame:
    rows = []
    for event_field in ("event_date", "cirp_admission_date"):
        for lead in settings["recall_leads"]:
            observations = strict_lead_observations(predictions, events, lead, event_field=event_field)
            if observations.empty:
                continue
            groups = [("overall", "all", observations)]
            groups += [(dimension, str(value), group) for dimension in ("sector", "period")
                       for value, group in observations.groupby(dimension, dropna=False)]
            for dimension, value, group in groups:
                hits, count = int(group.hit.sum()), len(group)
                low, high = wilson_interval(hits, count, settings["confidence"])
                rows.append({"arena": arena, "event_definition": event_field, "lead_quarters": lead,
                             "breakdown": dimension, "group": value, "events": count, "scored_events": int(group.scored.sum()),
                             "hits": hits, "recall": hits / count, "ci_low": low, "ci_high": high,
                             "needs_verification": int(group.scored.sum() < count), "is_synthetic": int(group.is_synthetic.eq(1).any())})
    return pd.DataFrame(rows)


def clustered_recall(observations: pd.DataFrame, membership: pd.DataFrame, confidence: float) -> dict:
    """Count a sourced corporate group once; unknown groups cannot imply independence."""
    if membership.entity_id.duplicated().any():
        raise ValueError("Ambiguous corporate-group membership")
    joined = observations.merge(membership[["entity_id", "group_id"]], on="entity_id", how="left", validate="many_to_one")
    if joined.group_id.isna().any():
        return {"recall": np.nan, "ci_low": np.nan, "ci_high": np.nan, "needs_verification": 1}
    hits = joined.groupby("group_id").hit.max()
    low, high = wilson_interval(int(hits.sum()), len(hits), confidence)
    return {"recall": hits.mean(), "ci_low": low, "ci_high": high, "needs_verification": 0}


def horizon_labels(quarters: pd.DataFrame, events: pd.DataFrame, horizon: int, censor_date: str) -> pd.Series:
    """y(i,t)=1 for a verified event in (t,t+h]; right-censored windows stay unknown."""
    known = events.loc[events.needs_verification.eq(0)].set_index("entity_id").event_date
    cutoff = pd.to_datetime(censor_date, utc=True)
    values = []
    for row in quarters.itertuples():
        day = pd.to_datetime(row.scoring_date, utc=True)
        end = day + pd.DateOffset(months=3 * horizon)
        event = pd.to_datetime(known.get(row.entity_id), utc=True)
        if end > cutoff or (pd.notna(event) and event <= day):
            values.append(np.nan)
        else:
            values.append(float(pd.notna(event) and day < event <= end))
    return pd.Series(values, index=quarters.index, name=f"y_{horizon}q")
