"""Detection-vs-lead curves evaluated only after a registered replay."""

import pandas as pd
import numpy as np

from prahari.data.asof import as_of
from prahari.eval.india_metrics import strict_lead_observations, wilson_interval
from prahari.features.soft import rating_symbol


def is_sub_ig(value: str, rating_settings: dict, settings: dict) -> bool | None:
    """Classify the sourced grade on its own long-/short-term rating scale."""
    symbol = rating_symbol(value, rating_settings)
    if symbol is None:
        return None
    scale, rank = symbol
    if scale == "default":
        return True
    order = "rating_order" if scale == "long" else "short_rating_order"
    grades = "sub_ig_long_grades" if scale == "long" else "sub_ig_short_grades"
    return rating_settings[order][rank-1] in settings[grades]


def rating_lead_comparison(predictions: pd.DataFrame, events: pd.DataFrame, rating_actions: pd.DataFrame,
                           settings: dict, rating_settings: dict, arena: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare pre-event first flags with the first *sourced public* sub-IG action.

    Quarter lead is the difference of calendar-quarter ordinals; day lead is
    also retained. Positive means PRAHARI flagged earlier. Publication, rather
    than an earlier action date learned later, determines rating availability.
    The paired median is descriptive of observed endpoints, not a claim that
    the supplied rating history establishes the first-ever downgrade.
    """
    rows = []
    prediction_dates = pd.to_datetime(predictions.scoring_date, utc=True)
    for case in events.loc[events.needs_verification.eq(0)].to_dict(orient="records"):
        event = pd.to_datetime(case["event_date"], utc=True)
        history = predictions.loc[predictions.entity_id.eq(case["entity_id"]) & prediction_dates.lt(event)]
        flags = history.loc[history.get("deep_review_4q", history.deep_review).eq(1)]
        first_flag = pd.to_datetime(flags.scoring_date, utc=True).min()
        visible = as_of(rating_actions, event)
        visible = visible.loc[visible.entity_id.eq(case["entity_id"])].copy()
        grades = visible.rating_to.map(lambda value: is_sub_ig(value, rating_settings, settings))
        sub_ig = visible.loc[grades.eq(True)].sort_values(["public_date", "period_end"])
        first_rating = sub_ig.iloc[0] if not sub_ig.empty else None
        rating_date = first_rating.public_date if first_rating is not None else pd.NaT
        paired = pd.notna(first_flag) and pd.notna(rating_date)
        quarter_lead = (rating_date.tz_localize(None).to_period("Q").ordinal -
                        first_flag.tz_localize(None).to_period("Q").ordinal) if paired else np.nan
        rows.append({"arena": arena, "entity_id": case["entity_id"], "event_date": event,
                     "first_prahari_flag_date": first_flag, "first_sourced_sub_ig_public_date": rating_date,
                     "rating_source_url": first_rating.source_url if first_rating is not None else None,
                     "lead_calendar_quarters": quarter_lead,
                     "lead_days": (rating_date-first_flag).days if paired else np.nan,
                     "comparison_status": "paired_observed" if paired else "missing_observed_endpoint",
                     "rating_history_scope": "available_source_actions_not_certified_complete_history",
                     "unrecognized_rating_actions": int(grades.isna().sum()),
                     "needs_verification": int(not paired or grades.isna().any()),
                     "is_synthetic": int(case["is_synthetic"] or predictions.is_synthetic.eq(1).any() or visible.is_synthetic.eq(1).any())})
    table = pd.DataFrame(rows)
    if table.empty:
        return table, pd.DataFrame()
    paired = table.loc[table.comparison_status.eq("paired_observed")]
    summary = pd.DataFrame([{"arena": arena, "cases": len(table), "paired_observed_cases": len(paired),
        "missing_prahari_flag_cases": int(table.first_prahari_flag_date.isna().sum()),
        "missing_sourced_sub_ig_cases": int(table.first_sourced_sub_ig_public_date.isna().sum()),
        "median_lead_calendar_quarters_paired_observed": paired.lead_calendar_quarters.median(),
        "median_lead_days_paired_observed": paired.lead_days.median(),
        "earlier_prahari_flags_paired_observed": int(paired.lead_days.gt(0).sum()),
        "interpretation": "descriptive_observed_endpoints_not_first_ever_rating_claim",
        "needs_verification": int(table.needs_verification.eq(1).any()),
        "is_synthetic": int(table.is_synthetic.eq(1).any())}])
    return table, summary


def detection_curve(predictions: pd.DataFrame, events: pd.DataFrame, settings: dict, arena: str, *, rating_actions=None, rating_settings=None) -> pd.DataFrame:
    rows = []
    for lead in range(settings["detection_max_lead"], -1, -1):
        observed = strict_lead_observations(predictions, events, lead, head="4q")
        if observed.empty:
            continue
        low, high = wilson_interval(int(observed.hit.sum()), len(observed), settings["confidence"])
        rating_hits, rating_known, altman_hits, altman_known = 0, 0, 0, 0
        for row in observed.itertuples():
            snapshot = predictions.loc[predictions.entity_id.eq(row.entity_id) & pd.to_datetime(predictions.scoring_date, utc=True).eq(row.required_scoring_date)]
            if not snapshot.empty:
                value = snapshot.iloc[0].get(settings["altman_distress_field"], np.nan)
                if pd.notna(value):
                    altman_known += 1
                    altman_hits += int(value < settings["altman_distress_threshold"])
            if rating_actions is not None and rating_settings is not None:
                dated = as_of(rating_actions, row.required_scoring_date)
                dated = dated.loc[dated.entity_id.eq(row.entity_id)].sort_values(["period_end", "public_date"])
                current = dated.groupby(["agency", "instrument"], dropna=False).tail(1)
                classifications = [is_sub_ig(value, rating_settings, settings) for value in current.rating_to]
                if classifications and all(value is not None for value in classifications):
                    rating_known += 1
                    rating_hits += int(any(classifications))
        rows.append({"arena": arena, "lead_quarters": lead, "events": len(observed), "hits": int(observed.hit.sum()),
                     "recall": observed.hit.mean(), "ci_low": low, "ci_high": high,
                     "rating_sub_ig_recall": rating_hits / len(observed) if rating_known == len(observed) else np.nan,
                     "rating_known_cases": rating_known,
                     "altman_distress_recall": altman_hits / len(observed) if altman_known == len(observed) else np.nan,
                     "altman_known_cases": altman_known,
                     "scored_events": int(observed.scored.sum()), "needs_verification": int(observed.scored.sum() < len(observed)),
                     "is_synthetic": int(observed.is_synthetic.eq(1).any())})
    return pd.DataFrame(rows)
