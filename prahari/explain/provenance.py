"""Chronological score changes with explicit time and peer-context effects."""

from collections.abc import Callable

import numpy as np
import pandas as pd


def telescoping_trace(items: pd.DataFrame, previous_date: str, scoring_date: str, previous_pd: float,
                      final_pd: float, score_prefix: Callable[[pd.DataFrame], float], *, tolerance: float) -> pd.DataFrame:
    """Re-score prefixes of actual newly public source items; do not invent rows.

    The roll-forward effect changes time while holding old evidence fixed.
    Remaining peer/universe-context change is explicit, never falsely assigned
    to a borrower document. The final deltas must telescope to the PD change.
    """
    start, end = pd.to_datetime(previous_date, utc=True), pd.to_datetime(scoring_date, utc=True)
    dates = pd.to_datetime(items.public_date, utc=True)
    if not dates.ge(start).all() or not dates.lt(end).all():
        raise ValueError("Evidence outside the scoring interval")
    if not np.isfinite([previous_pd, final_pd]).all():
        raise ValueError("Telescoping provenance needs two scored endpoints")
    ordered = items.sort_values(["public_date", "source_url"], kind="stable").reset_index(drop=True)
    synthetic = int(items.is_synthetic.eq(1).any())
    baseline = score_prefix(ordered.iloc[:0])
    if not np.isfinite(baseline):
        raise ValueError("Old-evidence roll-forward cannot be scored")
    rows = [{"step": 0, "kind": "time_roll_forward", "public_date": start, "source_url": None,
             "pd_before": previous_pd, "pd_after": baseline, "delta_pd": baseline - previous_pd, "is_synthetic": synthetic}]
    before = baseline
    for index, item in ordered.iterrows():
        after = score_prefix(ordered.iloc[:index + 1])
        if not np.isfinite(after):
            raise ValueError("An evidence prefix cannot be scored")
        rows.append({"step": index + 1, "kind": "borrower_source", "public_date": item.public_date,
                     "source_url": item.source_url, "pd_before": before, "pd_after": after,
                     "delta_pd": after - before, "is_synthetic": synthetic})
        before = after
    rows.append({"step": len(rows), "kind": "peer_and_universe_context", "public_date": end, "source_url": None,
                 "pd_before": before, "pd_after": final_pd, "delta_pd": final_pd - before, "is_synthetic": synthetic})
    result = pd.DataFrame(rows)
    if abs(result.delta_pd.sum() - (final_pd - previous_pd)) > tolerance:
        raise AssertionError("Source deltas do not telescope")
    return result
