"""Discover original annual-report links from public, unregistered document lists.

No logged-in exports, current financial tables or credentials are accessed.
Downloaded reports remain candidates until statement and publication review.
"""

from __future__ import annotations

from html.parser import HTMLParser
import json
import logging
import re
from urllib.parse import quote, urljoin, urlparse

import pandas as pd
import requests

from prahari.config import Config
from prahari.data.downloads import CachedDownloader, SourceBlocked
from prahari.data.firewall import write_real_table
from prahari.data.manual import read_manual
from prahari.data.uci import sha256_file

LOG = logging.getLogger(__name__)


class ReportLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.href: str | None = None
        self.label: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.synthetic = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attributes = dict(attrs)
        if tag == "meta" and attributes.get("name") == "is_synthetic":
            self.synthetic = int(attributes["content"])
        if tag == "a":
            self.href = attributes.get("href")
            self.label = []

    def handle_data(self, value: str) -> None:
        if self.href is not None:
            self.label.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.href is not None:
            self.links.append((" ".join(" ".join(self.label).split()), self.href))
            self.href = None


def annual_links(payload: bytes, page_url: str, pattern: str) -> list[tuple[int, str, int]]:
    """Select explicitly labelled annual reports; never infer a year from a URL."""
    parser = ReportLinks()
    parser.feed(payload.decode("utf-8"))
    result = []
    for label, href in parser.links:
        match = re.fullmatch(pattern, label)
        url = urljoin(page_url, href)
        if match and urlparse(url).scheme == "https" and urlparse(url).path.lower().endswith(".pdf"):
            result.append((int(match[1]), url, parser.synthetic))
    return sorted(set(result))


def discover_reports(config: Config, *, offline: bool, limit: int | None = None) -> None:
    settings = config.section("report_discovery_config")
    years_before = config.section("india_config")["panel"]["collection_years_before"]
    cases, peers = read_manual(config, "events"), read_manual(config, "peers")
    windows = {row.entity_id: pd.Timestamp(row.event_date).year for row in cases.itertuples()}
    cohort = [(row.entity_id, row.nse_symbol, row.bse_code, windows[row.entity_id])
              for row in cases.loc[cases.needs_verification.eq(0)].itertuples()]
    cohort += [(row.entity_id, row.symbols, None, windows[row.matched_to])
               for row in peers.loc[peers.needs_verification.eq(0)].itertuples()]
    cache = {}
    for document in config.section("source_config")["documents"]:
        cache[document["url"]] = (document["source"], document["filename"])
    for source in (settings["public_page_source"], settings["report_source"]):
        for receipt in (config.path("raw") / source).glob("*.receipt.json"):
            metadata = json.loads(receipt.read_text(encoding="utf-8"))
            cache[metadata["source_url"]] = (source, receipt.name.removesuffix(".receipt.json"))
    downloader = CachedDownloader(config)
    audit = []
    completed = 0
    try:
        for entity, symbol, bse_code, end_year in cohort:
            page = None
            symbols = [symbol] + ([str(bse_code)] if pd.notna(bse_code) else [])
            for candidate in symbols:
                page_url = settings["public_page_url"].format(symbol=quote(candidate, safe=""))
                source, filename = cache.get(page_url, (settings["public_page_source"], settings["public_page_filename"].format(
                    entity_id=entity, symbol=re.sub(r"[^A-Za-z0-9_+-]", "_", candidate), snapshot_date=settings["snapshot_date"])))
                try:
                    page = downloader.fetch(source, page_url, filename, offline=offline)
                    break
                except SourceBlocked:
                    raise
                except (FileNotFoundError, requests.RequestException) as exc:
                    LOG.warning("Public document list unavailable %s: %s", entity, type(exc).__name__)
            if page is None:
                audit.append({"entity_id": entity, "status": "document_list_unavailable", "needs_verification": 1, "is_synthetic": 0})
                continue
            links = annual_links(page.read_bytes(), page_url, settings["annual_label_pattern"])
            selected = [(year, url, synthetic) for year, url, synthetic in links if end_year-years_before <= year <= end_year]
            for year, url, synthetic in selected:
                if limit is not None and completed >= limit:
                    break
                source, filename = cache.get(url, (settings["report_source"], settings["report_filename"].format(entity_id=entity, year=year)))
                record = {"entity_id": entity, "report_label_year": year, "source_url": url,
                          "discovery_source": page_url, "needs_verification": 1, "is_synthetic": synthetic}
                try:
                    raw = downloader.fetch(source, url, filename, offline=offline)
                    cache[url] = (source, filename)
                    pdf = raw.read_bytes().startswith(b"%PDF-")
                    record.update(status="cached_original_candidate" if pdf else "non_pdf_response",
                                  source_doc=str(raw.relative_to(config.root)).replace("\\", "/"), sha256=sha256_file(raw))
                    completed += int(pdf)
                except SourceBlocked:
                    raise
                except (FileNotFoundError, requests.RequestException) as exc:
                    record.update(status="unavailable", reason=type(exc).__name__)
                audit.append(record)
                LOG.info("Original annual-report candidate %s year=%s status=%s; extraction not inferred", entity, year, record["status"])
            if limit is not None and completed >= limit:
                break
    finally:
        downloader.close()
        if audit:
            target = config.path("report_discovery_audit")
            table = pd.DataFrame(audit)
            if target.exists():
                table = pd.concat([pd.read_csv(target), table], ignore_index=True)
                table = table.drop_duplicates(["entity_id", "source_url"], keep="last")
            write_real_table(table, target)
