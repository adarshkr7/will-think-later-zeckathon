"""Within-firm timing randomization, never altering source event records."""

import numpy as np
import pandas as pd

from prahari.eval.india_metrics import strict_lead_observations


def within_firm_placebo(predictions, events, settings, seed, arena):
    """Relocate the lead snapshot among each case's replayed pre-event quarters.

    Only aggregate randomization statistics are exported. No invented dated
    source row is written. Missing probabilities abort that lead's null test.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for lead in settings["recall_leads"]:
        observed = strict_lead_observations(predictions, events, lead)
        pools = []
        for case in observed.itertuples():
            eligible = predictions.loc[predictions.entity_id.eq(case.entity_id) &
                pd.to_datetime(predictions.scoring_date, utc=True).lt(case.event_date)]
            if eligible.empty or eligible[f"pd_{lead}q"].isna().any():
                pools = []
                break
            pools.append(eligible.get(f"deep_review_{lead}q", eligible.deep_review).to_numpy())
        valid = bool(pools) and observed.scored.eq(1).all()
        null = np.array([np.mean([rng.choice(pool) for pool in pools]) for _ in range(settings["placebo_runs"])]) if valid else np.array([])
        alpha = (1 - settings["confidence"]) / 2
        actual = observed.hit.mean() if valid else np.nan
        rows.append({"arena": arena, "lead_quarters": lead, "observed_recall": actual,
                     "null_mean": null.mean() if valid else np.nan,
                     "null_ci_low": np.quantile(null, alpha) if valid else np.nan,
                     "null_ci_high": np.quantile(null, 1-alpha) if valid else np.nan,
                     "p_value": (1 + (null >= actual).sum()) / (1 + len(null)) if valid else np.nan,
                     "runs": len(null), "status": "completed" if valid else "incomplete_case_history",
                     "is_synthetic": int(events.is_synthetic.eq(1).any() or predictions.is_synthetic.eq(1).any())})
    return pd.DataFrame(rows)
