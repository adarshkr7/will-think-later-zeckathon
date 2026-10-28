"""Dated soft signals. An empty event search is unknown rather than a negative."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from prahari.features.common import require_snapshot


def rating_symbol(text: str, settings: dict) -> tuple[str, int] | None:
    """Normalize explicit domestic symbols; never compare short to long ratings.

    ICRA CreditRatingScale and CARE Rating_Symbols_pursuant (2022): modifiers
    AA through C yield twenty long-term symbols. The plan's D=22 is not used
    to invent two additional grades. Withdrawn/unknown symbols stay unknown.
    """
    raw = re.sub(r"^(?:\[ICRA\]|ICRA|CARE|CRISIL|INDIA RATINGS|IND|ACUITE)\s*", "", str(text).strip().upper())
    for kind, order in (("short", settings["short_rating_order"]), ("long", settings["rating_order"])):
        for symbol in sorted(order, key=len, reverse=True):
            if re.match(re.escape(symbol) + r"(?=$|[\s/(])", raw):
                return kind, order.index(symbol) + 1
    return None


def soft_features(entities: pd.DataFrame, pledges: pd.DataFrame, ratings: pd.DataFrame,
                  governance: pd.DataFrame, settings: dict) -> pd.DataFrame:
    for table in (entities, pledges, ratings, governance):
        require_snapshot(table)
    cutoff = pd.Timestamp(entities.attrs["as_of"])
    if any(table.attrs["as_of"] != entities.attrs["as_of"] for table in (pledges, ratings, governance)):
        raise ValueError("Soft-signal cutoffs differ")
    names = ["pledge_pct", "pledge_delta_4q", "auditor_exit_8q", "rating_notch_delta_4q", "rating_watch_neg_or_inc", "delayed_filing_4q", "audit_red_flag_count", "governance_flag_count"]
    rows = []
    for record in entities.to_dict(orient="records"):
        entity = record["entity_id"]
        row = {"entity_id": entity, **{name: np.nan for name in names}, **{name + "__reason": "coverage_unknown" for name in names}}
        dates = [pd.to_datetime(record["max_source_date"], utc=True)]
        synthetic = int(record["is_synthetic"])
        p = pledges.loc[pledges.entity_id.eq(entity)].sort_values(["period_end", "public_date"])
        r = ratings.loc[ratings.entity_id.eq(entity)].sort_values(["period_end", "public_date"])
        g = governance.loc[governance.entity_id.eq(entity)]
        for table in (p, r, g):
            if not table.empty:
                dates.append(table.max_source_date.max())
                synthetic |= int(table.is_synthetic.eq(1).any())
        def set_value(name: str, value: float) -> None:
            if pd.notna(value):
                row[name], row[name + "__reason"] = float(value), ""
        if not p.empty:
            latest = p.iloc[-1]
            set_value("pledge_pct", latest.promoter_pledged_pct_of_promoter)
            previous = p.loc[p.period_end.eq(latest.period_end - pd.DateOffset(years=1))]
            if not previous.empty:
                set_value("pledge_delta_4q", latest.promoter_pledged_pct_of_promoter - previous.iloc[-1].promoter_pledged_pct_of_promoter)
        auditor = g.loc[g.event_type.eq("auditor_resignation") & g.period_end.ge(cutoff - pd.DateOffset(months=3 * settings["auditor_window_quarters"]))]
        if not auditor.empty:
            set_value("auditor_exit_8q", 1)
        window = g.loc[g.period_end.ge(cutoff - pd.DateOffset(months=3 * settings["governance_window_quarters"]))]
        if window.event_type.eq("delayed_results").any():
            set_value("delayed_filing_4q", 1)
        # No total count without a complete search denominator; positive
        # events above are directly observed rather than inferred negatives.
        if not r.empty:
            current = r.groupby(["agency", "instrument"], dropna=False).tail(1)
            negative = current.watch.astype(str).str.casefold().isin(settings["negative_watch_values"]) | current.outlook.astype(str).str.casefold().eq("negative") | current.inc_flag.eq(1)
            known_watch = current.inc_flag.notna() & (current.watch.notna() | current.outlook.notna())
            if negative.any():
                set_value("rating_watch_neg_or_inc", 1)
            elif known_watch.all():
                set_value("rating_watch_neg_or_inc", 0)
            deltas = []
            for latest in current.itertuples():
                past = r.loc[r.agency.eq(latest.agency) & r.instrument.eq(latest.instrument)
                             & r.period_end.le(cutoff - pd.DateOffset(years=1))]
                if past.empty:
                    continue
                old, new = rating_symbol(past.iloc[-1].rating_to, settings), rating_symbol(latest.rating_to, settings)
                if old and new and old[0] == new[0]:
                    deltas.append(new[1] - old[1])
            if deltas:
                set_value("rating_notch_delta_4q", max(deltas))
        audit = [record.get(name, np.nan) for name in ("going_concern_flag", "caro_default_flag", "caro_fraud_flag")]
        if all(pd.notna(value) and value in (0, 1) for value in audit):
            set_value("audit_red_flag_count", sum(audit))
        row["max_source_date"] = max((date for date in dates if pd.notna(date)), default=pd.NaT)
        row["is_synthetic"] = synthetic
        rows.append(row)
    result = pd.DataFrame(rows, columns=["entity_id", *names, *[name + "__reason" for name in names], "max_source_date", "is_synthetic"])
    result.attrs.update(entities.attrs)
    return result
