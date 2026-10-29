"""Exchange-session counts and calendars certified by complete source censuses."""

from __future__ import annotations

import re

import pandas as pd
from openpyxl import load_workbook
from pypdf import PdfReader

from prahari.config import Config
from prahari.data.downloads import CachedDownloader
from prahari.data.entity_review import require_reviewed_text
from prahari.data.uci import sha256_file


def reviewed_session_counts(config: Config, client: CachedDownloader, *, offline: bool) -> pd.DataFrame:
    """Read exact cash-segment counts, with pinned venue headings and source cells."""
    settings = config.section("calendar_config")
    rows = []
    for source in settings["count_sources"]:
        raw = client.fetch(source["source"], source["url"], source["filename"], offline=offline)
        if sha256_file(raw) != source["sha256"]:
            raise ValueError("Reviewed session-count source changed")
        values = []
        if source["format"] == "xlsx":
            workbook = load_workbook(raw, read_only=True, data_only=True)
            try:
                sheet = workbook[source["sheet"]]
                for cell, expected in source["header_cells"].items():
                    if str(sheet[cell].value).strip() != expected:
                        raise ValueError("Session-count venue or column heading changed")
                for index in range(source["first_row"], source["last_row"]+1):
                    label = str(sheet[f"{source['period_column']}{index}"].value)
                    cell = f"{source['count_column']}{index}"
                    values.append((label, sheet[cell].value, f"{source['sheet']}!{cell}"))
            finally:
                workbook.close()
        elif source["format"] == "pdf":
            text = PdfReader(raw).pages[source["page"]-1].extract_text()
            require_reviewed_text(text, source["evidence_markers"])
            values = [(match["period"], int(match["count"]), f"page={source['page']}")
                      for match in re.finditer(source["row_pattern"], text, re.MULTILINE)]
        else:
            raise ValueError("Unsupported session-count source format")
        selected = [(label, value, ref) for label, value, ref in values if label in source["period_labels"]]
        if len(selected) != len(source["period_labels"]) or len({label for label, _, _ in selected}) != len(selected):
            raise ValueError("Missing or ambiguous reviewed fiscal session count")
        for label, value, ref in selected:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value or value <= 0:
                raise ValueError("Published session count is not a positive integer")
            first, last = label.split("-")
            if (int(first)+1) % 100 != int(last):
                raise ValueError("Invalid source fiscal-year label")
            year_end = settings["fiscal_year_end"]
            begin = pd.Timestamp(year=int(first), month=year_end["month"], day=year_end["day"], tz="UTC") + pd.Timedelta(days=1)
            end = pd.Timestamp(year=int(first)+1, month=year_end["month"], day=year_end["day"], tz="UTC")
            if value > (end-begin).days+1:
                raise ValueError("Session count exceeds its civil-date interval")
            rows.append({"entity_id": settings["exchange"], "field": "session_count__"+source["id"],
                         "period_start": begin.date().isoformat(), "period_end": end.date().isoformat(),
                         "expected_count": int(value), "public_date": source["public_date"],
                         "source_url": source["url"]+"#"+ref, "date_is_imputed": source["date_is_imputed"],
                         "needs_verification": 0, "is_synthetic": 0})
    return pd.DataFrame(rows, columns=config.section("manual_config")["tables"]["trading_session_counts"]["columns"])


def certify_period(sessions: pd.DataFrame, claims: pd.DataFrame, start: pd.Timestamp,
                   end: pd.Timestamp, exchange: str, census_ref: str) -> tuple[pd.DataFrame, dict]:
    """Certify a bounded calendar only when independent exact totals reconcile.

    Let S be the actual trading-day set and K the set proved by original
    production bhavcopies. Those sources establish K as a subset of S.
    A separately published exact count |S|=|K| establishes S=K. Only then
    is its civil-date complement known to be non-trading. A missing archive
    alone proves nothing. Conflicting counts or excess observations fail.
    """
    if "as_of" not in sessions.attrs or "as_of" not in claims.attrs:
        raise ValueError("Session certification requires dated as_of inputs")
    first, last = pd.to_datetime(start, utc=True), pd.to_datetime(end, utc=True)
    actual = sessions.loc[sessions.entity_id.eq(exchange) & sessions.period_end.between(first, last)]
    views = claims.loc[claims.entity_id.eq(exchange) & claims.period_end.eq(last)
                       & pd.to_datetime(claims.period_start, utc=True).eq(first)]
    if actual.period_end.duplicated().any():
        raise ValueError("A trading day cannot count twice in a session census")
    numbers = pd.to_numeric(views.expected_count, errors="raise")
    if numbers.isna().any() or numbers.le(0).any() or numbers.mod(1).ne(0).any():
        raise ValueError("Unknown or non-integral session counts cannot certify a calendar")
    totals = set(numbers.astype(int))
    expected = next(iter(totals)) if len(totals) == 1 else None
    status = ("count_source_missing" if not totals else "count_source_conflict" if len(totals) != 1 else
              "complete_census" if len(actual) == expected else
              "excess_observations" if len(actual) > expected else "incomplete_census")
    complete = status == "complete_census"
    taint = int(actual.is_synthetic.eq(1).any() or views.is_synthetic.eq(1).any())
    audit = {"entity_id": exchange, "period_start": first, "period_end": last,
             "observed_sessions": len(actual), "expected_sessions": expected,
             "count_claims": len(views), "status": status, "needs_verification": int(not complete),
             "is_synthetic": taint}
    columns = ["entity_id", "period_end", "public_date", "is_trading_day", "source_url",
               "date_is_imputed", "needs_verification", "is_synthetic"]
    if not complete:
        # Keep only positively proved sessions. Closed dates remain unknown.
        rows = actual.reindex(columns=columns).copy()
        rows["is_trading_day"] = 1
        return rows, audit
    publication = max(actual.max_source_date.max(), views.max_source_date.max())
    imputed = int(actual.date_is_imputed.eq(1).any() or views.date_is_imputed.eq(1).any())
    dates = set(actual.period_end)
    proof = ";".join([*dict.fromkeys(views.source_url), census_ref])
    rows = [{"entity_id": exchange, "period_end": day, "public_date": publication,
             "is_trading_day": int(day in dates), "source_url": proof,
             "date_is_imputed": imputed, "needs_verification": 0, "is_synthetic": taint}
            for day in pd.date_range(first, last, freq="D")]
    return pd.DataFrame(rows, columns=columns), audit
