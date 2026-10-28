"""Event evidence validation. Outcomes are consumed by evaluation only."""

from __future__ import annotations

import pandas as pd


def earliest_event_date(record: dict) -> pd.Timestamp:
    """Earliest sourced payment default, qualifying CRA D, or CIRP admission.

    Under the human-approved uncured-d-v1 rule, first_D_rating_date is
    curated to exclude a D later cured to investment/normal grade before
    final default. Unknown components stay empty, with coverage limitations
    documented. This helper never infers missing dates or cure histories.
    """
    if record["needs_verification"] != 0:
        return pd.NaT
    candidates = [pd.to_datetime(record.get(key), utc=True) for key in
                  ("first_payment_default_date", "first_D_rating_date", "cirp_admission_date")]
    known = [value for value in candidates if pd.notna(value)]
    if not known or pd.isna(record.get("source_urls")):
        raise ValueError("A verified event needs sourced evidence")
    return min(known)


def qualifying_event_evidence(evidence: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Apply the same human-approved cure rule to every company's D evidence.

    This is outcome curation for evaluation, never a primary-model input.
    An absent cure determination cannot be interpreted as an uncured D.
    """
    if not settings["exclude_d_cured_before_final_default"]:
        raise ValueError("The registered event rule excludes cured D episodes")
    known = evidence.loc[evidence.needs_verification.eq(0)].copy()
    ratings = known.event_type.eq("D_rating")
    if known.loc[ratings, "cured_before_final_default"].isna().any():
        raise ValueError("D evidence needs a human-verified cure determination")
    if not known.event_rule_version.eq(settings["rule_version"]).all():
        raise ValueError("Event evidence uses a different event rule")
    return known.loc[~ratings | known.cured_before_final_default.eq(0)].copy()


def validate_event_evidence(events: pd.DataFrame, evidence: pd.DataFrame, settings: dict) -> None:
    """Reconcile component dates and earliest-event publication, without backdating.

    The company table is an evaluation label catalog. Later components retain
    their own public dates in event_evidence and are not historical features.
    """
    known = qualifying_event_evidence(evidence, settings)
    fields = {"payment_default": "first_payment_default_date", "D_rating": "first_D_rating_date",
              "cirp": "cirp_admission_date"}
    for record in events.loc[events.needs_verification.eq(0)].to_dict(orient="records"):
        components = known.loc[known.entity_id.eq(record["entity_id"])].copy()
        if components.empty:
            raise ValueError("Verified event lacks component-level review evidence")
        components["period_end"] = pd.to_datetime(components.period_end, utc=True)
        for kind, field in fields.items():
            dates = components.loc[components.event_type.eq(kind), "period_end"]
            actual = pd.to_datetime(record[field], utc=True)
            expected = dates.min()
            if not ((pd.isna(actual) and pd.isna(expected)) or actual == expected):
                raise ValueError(f"Event component disagrees with qualifying evidence: {field}")
        event = earliest_event_date(record)
        if event != pd.to_datetime(record["event_date"], utc=True):
            raise ValueError("Event date differs from earliest qualifying component")
        publication = pd.to_datetime(components.loc[components.period_end.eq(event), "public_date"], utc=True).min()
        if publication != pd.to_datetime(record["public_date"], utc=True):
            raise ValueError("Event public date differs from its first source publication")
