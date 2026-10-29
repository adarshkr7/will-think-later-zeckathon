"""Audit panel market coverage against a verified exchange-session calendar."""

from __future__ import annotations

import pandas as pd


def equity_calendar(calendar: pd.DataFrame, exceptions: pd.DataFrame) -> pd.DataFrame:
    """Scope cash-segment sessions to company equities using positive evidence.

    Cash-segment totals also include a gold-ETF-only Sunday. Retain the original
    cash census and record equity scope separately. Absence of a company quote
    never establishes an exception. These are retrospective coverage inputs,
    not score features or historical publication-date overrides.
    """
    result = calendar.copy()
    result["is_equity_trading_day"] = result.is_trading_day
    result["equity_scope_source"] = ""
    if exceptions.empty:
        return result
    if "as_of" not in exceptions.attrs:
        raise ValueError("Equity scope evidence must pass through as_of")
    if (exceptions.period_end.duplicated().any() or exceptions.source_url.isna().any()
            or exceptions.source_url.astype(str).str.strip().eq("").any()):
        raise ValueError("Equity scope needs unique dates and original provenance")
    for proof in exceptions.itertuples():
        selected = pd.to_datetime(result.period_end, utc=True).eq(proof.period_end)
        if not selected.any():
            continue
        if result.loc[selected, "needs_verification"].ne(0).any():
            raise ValueError("Unknown cash-session dates cannot be scoped as complete")
        result.loc[selected, "is_equity_trading_day"] = 0
        result.loc[selected, "equity_scope_source"] = proof.source_url
        result.loc[selected, "is_synthetic"] = result.loc[selected, "is_synthetic"].astype(int) | int(proof.is_synthetic)
    return result


def market_coverage(windows: pd.DataFrame, prices: pd.DataFrame, calendar: pd.DataFrame,
                    listings: pd.DataFrame | None = None, *, exchange: str | None = None) -> pd.DataFrame:
    """A missing file is not evidence of an exchange holiday or a delisting.

    A complete calendar must explicitly cover every civil date in the requested
    interval with sourced trading/non-trading status. Missing/unknown calendar
    rows prevent a completeness claim, rather than reducing the denominator.

    Verified first-listing certificates can explain a structural pre-listing
    interval. Full-window quote coverage remains a separate flag; the source
    audit does not fill prices or remove firms from an evaluation denominator.
    """
    rows = []
    certificates = pd.DataFrame()
    if listings is not None and not listings.empty:
        required = {"entity_id", "exchange", "listing_date", "source_url", "needs_verification", "is_synthetic"}
        if not exchange or not required.issubset(listings):
            raise ValueError("Listing certificates require an explicit exchange and provenance")
        certificates = listings.loc[listings.needs_verification.eq(0) & listings.exchange.eq(exchange)].copy()
        if (certificates.entity_id.duplicated().any() or certificates.source_url.isna().any()
                or certificates.source_url.astype(str).str.strip().eq("").any()):
            raise ValueError("Missing or ambiguous first-listing certificate")
        certificates["listing_date"] = pd.to_datetime(certificates.listing_date, utc=True)
        if certificates.listing_date.isna().any():
            raise ValueError("Unknown first-listing date cannot exclude market sessions")
        certificates = certificates.set_index("entity_id")
    if not calendar.empty:
        required = {"period_end", "is_trading_day", "source_url", "needs_verification", "is_synthetic"}
        if not required.issubset(calendar) or not calendar.is_trading_day.isin([0, 1]).all():
            raise ValueError("Calendar needs sourced, explicit trading-day status")
        if "is_equity_trading_day" in calendar and not calendar.is_equity_trading_day.isin([0, 1]).all():
            raise ValueError("Equity-session scope must be explicit")
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
        scope = "is_equity_trading_day" if "is_equity_trading_day" in known else "is_trading_day"
        full_expected = set(known.loc[known[scope].eq(1), "period_end"]) & set(days) if calendar_ok else set()
        non_equity = known.loc[known.is_trading_day.eq(1) & known[scope].eq(0) & known.period_end.isin(days)] if calendar_ok else known.iloc[:0]
        listed, listing_source = pd.NaT, None
        if not certificates.empty and window["entity_id"] in certificates.index:
            proof = certificates.loc[window["entity_id"]]
            listed, listing_source = proof.listing_date, proof.source_url
        excluded = {day for day in full_expected if day < listed} if pd.notna(listed) else set()
        expected = full_expected - excluded
        observations = prices.loc[prices.entity_id.eq(window["entity_id"]) & prices.needs_verification.eq(0)]
        observed = set(pd.to_datetime(observations.period_end, utc=True)) & set(days)
        complete = calendar_ok and bool(expected) and expected == observed
        rows.append({"entity_id": window["entity_id"], "start": start, "end": end,
                     "calendar_complete": int(calendar_ok), "observed_sessions": len(observed),
                     "first_listing_date": listed, "listing_source_url": listing_source,
                     "excluded_pre_listing_sessions": len(excluded) if calendar_ok else None,
                     "excluded_non_equity_sessions": len(non_equity) if calendar_ok else None,
                     "equity_scope_source_url": ";".join(dict.fromkeys(non_equity.equity_scope_source)) if "equity_scope_source" in non_equity else "",
                     "full_window_quote_history": int(calendar_ok and bool(full_expected) and full_expected == observed),
                     "expected_sessions": len(expected) if calendar_ok else None,
                     "missing_sessions": len(expected - observed) if calendar_ok else None,
                     "unexpected_sessions": len(observed - expected) if calendar_ok else None,
                     "complete": int(complete), "needs_verification": int(not complete),
                     "is_synthetic": int(window["is_synthetic"] or prices.is_synthetic.eq(1).any() or
                                         (not calendar.empty and calendar.is_synthetic.eq(1).any()) or
                                         (listings is not None and not listings.empty and listings.is_synthetic.eq(1).any()))})
    return pd.DataFrame(rows, columns=["entity_id", "start", "end", "calendar_complete", "observed_sessions",
                                      "first_listing_date", "listing_source_url", "excluded_pre_listing_sessions", "excluded_non_equity_sessions", "equity_scope_source_url", "full_window_quote_history",
                                      "expected_sessions", "missing_sessions", "unexpected_sessions", "complete", "needs_verification", "is_synthetic"])
