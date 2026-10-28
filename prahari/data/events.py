"""Event evidence validation. Outcomes are consumed by evaluation only."""

from __future__ import annotations

import pandas as pd


def earliest_event_date(record: dict) -> pd.Timestamp:
    """Plan §2.2: earliest sourced payment default, CRA D, or CIRP admission.

    An incomplete search cannot be upgraded into a verified earliest event.
    This helper validates verified input; it does not infer missing dates.
    """
    if record["needs_verification"] != 0:
        return pd.NaT
    candidates = [pd.to_datetime(record.get(key), utc=True) for key in
                  ("first_payment_default_date", "first_D_rating_date", "cirp_admission_date")]
    known = [value for value in candidates if pd.notna(value)]
    if not known or pd.isna(record.get("source_urls")):
        raise ValueError("A verified event needs sourced evidence")
    return min(known)
