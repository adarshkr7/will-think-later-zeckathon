"""Audit panel market coverage against a verified exchange-session calendar."""

from __future__ import annotations

import pandas as pd


def market_coverage(windows: pd.DataFrame, prices: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    """A missing file is not evidence of an exchange holiday or a delisting.

    A complete calendar must explicitly cover every civil date in the requested
    interval with sourced trading/non-trading status. Missing/unknown calendar
    rows prevent a completeness claim, rather than reducing the denominator.
    """
    rows = []
    if not calendar.empty:
        required = {"period_end", "is_trading_day", "source_url", "needs_verification", "is_synthetic"}
        if not required.issubset(calendar) or not calendar.is_trading_day.isin([0, 1]).all():
            raise ValueError("Calendar needs sourced, explicit trading-day status")
        verified = calendar.loc[calendar.needs_verification.eq(0)]
        if verified.source_url.isna().any() or verified.source_url.astype(str).str.strip().eq("").any():
            raise ValueError("Verified calendar rows lack provenance")
        if calendar.period_end.duplicated().any():
            raise ValueError("Coverage requires a single exchange calendar with unique dates")
    for window in windows.to_dict(orient="records"):
        start, end = pd.to_datetime(window["start"], utc=True), pd.to_datetime(window["end"], utc=True)
        days = pd.date_range(start.normalize(), end.normalize(), freq="D")
        known = calendar.loc[calendar.needs_verification.eq(0)].copy() if not calendar.empty else calendar
        if not known.empty:
            known["period_end"] = pd.to_datetime(known.period_end, utc=True)
        calendar_ok = not known.empty and set(days).issubset(set(known.period_end))
        expected = set(known.loc[known.is_trading_day.eq(1), "period_end"]) & set(days) if calendar_ok else set()
        observations = prices.loc[prices.entity_id.eq(window["entity_id"]) & prices.needs_verification.eq(0)]
        observed = set(pd.to_datetime(observations.period_end, utc=True)) & set(days)
        complete = calendar_ok and bool(expected) and expected == observed
        rows.append({"entity_id": window["entity_id"], "start": start, "end": end,
                     "calendar_complete": int(calendar_ok), "observed_sessions": len(observed),
                     "expected_sessions": len(expected) if calendar_ok else None,
                     "missing_sessions": len(expected - observed) if calendar_ok else None,
                     "unexpected_sessions": len(observed - expected) if calendar_ok else None,
                     "complete": int(complete), "needs_verification": int(not complete),
                     "is_synthetic": int(window["is_synthetic"] or prices.is_synthetic.eq(1).any() or
                                         (not calendar.empty and calendar.is_synthetic.eq(1).any()))})
    return pd.DataFrame(rows, columns=["entity_id", "start", "end", "calendar_complete", "observed_sessions",
                                      "expected_sessions", "missing_sessions", "unexpected_sessions", "complete", "needs_verification", "is_synthetic"])
