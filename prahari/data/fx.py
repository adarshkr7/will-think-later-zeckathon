"""Original H.10 release vintages, never today's revised historical FRED series."""

from __future__ import annotations

from html.parser import HTMLParser
import json
import logging
import re

import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.downloads import CachedDownloader, SourceUnavailable
from prahari.data.firewall import write_real_table
from prahari.data.manual import read_manual

LOG = logging.getLogger(__name__)


class ReleaseHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.text: list[str] = []
        self.row_stack: list[list[str]] = []
        self.cell_stack: list[list[str]] = []
        self.synthetic = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attributes = dict(attrs)
        if tag == "meta" and attributes.get("name") == "is_synthetic":
            self.synthetic = int(attributes["content"])
        if tag == "tr":
            self.row_stack.append([])
        if tag in ("td", "th"):
            self.cell_stack.append([])

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self.cell_stack:
            self.cell_stack[-1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self.cell_stack:
            value = " ".join(" ".join(self.cell_stack.pop()).split())
            if self.row_stack:
                self.row_stack[-1].append(value)
        if tag == "tr" and self.row_stack:
            self.rows.append(self.row_stack.pop())


def parse_release(payload: bytes, source_url: str, expected_date: str, settings: dict) -> pd.DataFrame:
    page = ReleaseHTML()
    page.feed(payload.decode("utf-8-sig"))
    text = " ".join(" ".join(page.text).split())
    match = re.search(r"Release\s+Date:\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})", text)
    if not match:
        raise ValueError("H.10 release has no original publication date")
    public = pd.to_datetime(match[1], format="%B %d, %Y", utc=True)
    if public != pd.to_datetime(expected_date, utc=True):
        raise ValueError("H.10 release date differs from its official calendar")
    if "currency units per U.S. dollar" not in text:
        raise ValueError("H.10 exchange-rate units changed")
    headers = [row for row in page.rows if len(row) == 7 and row[0].casefold() == "country" and row[1].casefold() == "currency"]
    countries = [row for row in page.rows if len(row) == 7 and row[0].upper() == settings["country"]]
    if len(headers) != 1 or len(countries) != 1 or countries[0][1].upper() != settings["currency"]:
        raise ValueError("H.10 dated columns or currency row are absent/ambiguous")
    records = []
    for heading, amount in zip(headers[0][2:], countries[0][2:], strict=True):
        date_match = re.fullmatch(r"([A-Za-z]+)\.?\s+(\d{1,2})(?:,?\s+(\d{4}))?", heading)
        if not date_match:
            raise ValueError("Unsupported H.10 observation-date heading")
        month = pd.to_datetime(date_match[1][:3], format="%b").month
        year = int(date_match[3]) if date_match[3] else public.year
        period = pd.Timestamp(year, month, int(date_match[2]), tz="UTC")
        if not date_match[3] and period > public:
            period -= pd.DateOffset(years=1)
        if period >= public or (public-period).days > settings["maximum_release_lag_days"]:
            raise ValueError("H.10 observation is outside its original weekly release")
        missing = amount.upper() in settings["missing_tokens"]
        value = float("nan") if missing else float(amount)
        if not missing and (not pd.notna(value) or value <= 0):
            raise ValueError("Invalid sourced INR/USD rate")
        records.append({"entity_id": settings["entity_id"], "period_end": period.date().isoformat(),
                        "public_date": public.date().isoformat(), "inr_per_usd": value,
                        "source_url": source_url, "date_is_imputed": 0, "needs_verification": int(missing),
                        "is_synthetic": page.synthetic})
    return pd.DataFrame(records)


def collect_fx(config: Config, *, offline: bool) -> None:
    settings = config.section("fx_config")
    dates = config.section("feature_config")["dates"]
    downloader = CachedDownloader(config)
    try:
        calendar = downloader.fetch(settings["source"], settings["calendar_url"], settings["calendar_filename"], offline=offline)
        source_dates = json.loads(calendar.read_text(encoding="utf-8-sig"))
        releases = sorted({date for year in source_dates for month in year["Months"] for date in month["Dates"]})
        parsed = pd.to_datetime(releases, format="%Y%m%d", utc=True)
        quarters = pd.date_range(dates["first_quarter"], dates["last_quarter"], freq="QE-MAR", tz="UTC")
        selected = {}
        for quarter in quarters:
            eligible = parsed[parsed < quarter]
            if not len(eligible):
                raise ValueError("No official H.10 release before requested quarter")
            selected[quarter] = eligible.max().strftime("%Y%m%d")
        tables = []
        for date in sorted(set(selected.values())):
            url = settings["release_url"].format(date=date)
            try:
                raw = downloader.fetch(settings["source"], url, settings["release_filename"].format(date=date), offline=offline)
            except SourceUnavailable:
                LOG.warning("Original H.10 release unavailable: %s; rate remains unknown", url)
                continue
            table = parse_release(raw.read_bytes(), url, pd.Timestamp(date).date().isoformat(), settings)
            tables.append(table)
            LOG.info("Original H.10 %s rows=%s dates_imputed=0 missing_rates=%s", date, len(table), int(table.inr_per_usd.isna().sum()))
        existing = read_manual(config, "fx_rates")
        combined = pd.concat([existing, *tables], ignore_index=True).drop_duplicates()
        keys = ["entity_id", "period_end", "public_date"]
        if combined.duplicated(keys).any():
            raise ValueError("Conflicting original FX observations; no manual values overwritten")
        write_real_table(combined, config.path("manual") / "fx_rates.csv")
        rows = []
        maximum_age = config.section("feature_config")["chs"]["maximum_fx_age_days"]
        for quarter in quarters:
            visible = as_of(combined, quarter).sort_values(["period_end", "public_date"])
            visible = visible.loc[visible.period_end.ge(quarter-pd.Timedelta(days=maximum_age))]
            latest = visible.iloc[-1] if not visible.empty else None
            rows.append({"quarter": quarter.date().isoformat(), "available": int(latest is not None),
                         "observation_date": latest.period_end if latest is not None else pd.NaT,
                         "public_date": latest.public_date if latest is not None else pd.NaT,
                         "source_url": latest.source_url if latest is not None else None,
                         "needs_verification": int(latest is None), "is_synthetic": 0})
        write_real_table(pd.DataFrame(rows), config.path("fx_coverage"))
    finally:
        downloader.close()
