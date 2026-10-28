"""Detection-vs-lead curves evaluated only after a registered replay."""

import pandas as pd
import numpy as np

from prahari.eval.india_metrics import strict_lead_observations, wilson_interval


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
                from prahari.data.asof import as_of
                from prahari.features.soft import rating_symbol
                dated = as_of(rating_actions, row.required_scoring_date)
                dated = dated.loc[dated.entity_id.eq(row.entity_id)].sort_values(["period_end", "public_date"])
                current = dated.groupby(["agency", "instrument"], dropna=False).tail(1)
                symbols = [rating_symbol(value, rating_settings) for value in current.rating_to]
                if symbols and all(symbol is not None for symbol in symbols):
                    rating_known += 1
                    rating_hits += int(any(symbol[0] == "default" or
                        (symbol[0] == "long" and rating_settings["rating_order"][symbol[1]-1] in settings["sub_ig_long_grades"]) or
                        (symbol[0] == "short" and rating_settings["short_rating_order"][symbol[1]-1] in settings["sub_ig_short_grades"]) for symbol in symbols))
        rows.append({"arena": arena, "lead_quarters": lead, "events": len(observed), "hits": int(observed.hit.sum()),
                     "recall": observed.hit.mean(), "ci_low": low, "ci_high": high,
                     "rating_sub_ig_recall": rating_hits / len(observed) if rating_known == len(observed) else np.nan,
                     "rating_known_cases": rating_known,
                     "altman_distress_recall": altman_hits / len(observed) if altman_known == len(observed) else np.nan,
                     "altman_known_cases": altman_known,
                     "scored_events": int(observed.scored.sum()), "needs_verification": int(observed.scored.sum() < len(observed)),
                     "is_synthetic": int(observed.is_synthetic.eq(1).any())})
    return pd.DataFrame(rows)
