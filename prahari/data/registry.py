"""Public IBBI announcement discovery; absence alone never certifies survival."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse
import logging

import pandas as pd

from prahari.config import Config
from prahari.data.downloads import CachedDownloader
from prahari.data.firewall import write_real_table
from prahari.data.uci import sha256_file

LOG = logging.getLogger(__name__)


class AnnouncementPage(HTMLParser):
    def __init__(self, headers: list[str]) -> None:
        super().__init__()
        self.headers = headers
        self.rows: list[list[dict]] = []
        self.links: list[str] = []
        self.row: list[dict] | None = None
        self.cell: dict | None = None
        self.active = False
        self.found_header = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = {"text": [], "links": []}
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
            if self.cell is not None:
                self.cell["links"].append(attrs["href"])

    def handle_data(self, value):
        if self.cell is not None:
            self.cell["text"].append(value)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.cell["text"] = " ".join(" ".join(self.cell["text"]).split())
            if self.row is not None:
                self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row:
            values = [cell["text"] for cell in self.row]
            if values == self.headers:
                self.active = self.found_header = True
            elif self.active:
                if len(values) != len(self.headers):
                    raise ValueError("Public announcement table columns changed")
                self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            self.active = False


def parse_announcements(payload: str, source_url: str, settings: dict, *, page: int, is_synthetic: int) -> tuple[list[dict], int]:
    parser = AnnouncementPage(settings["headers"])
    parser.feed(payload)
    if not parser.found_header or not parser.rows:
        raise ValueError("Missing/empty original public announcement table")
    endpoint = urlparse(settings["url"])
    pages = [page]
    for link in parser.links:
        parsed = urlparse(urljoin(source_url, link))
        if parsed.netloc == endpoint.netloc and parsed.path == endpoint.path:
            value = parse_qs(parsed.query).get("page", [])
            if value:
                if len(value) != 1 or not value[0].isdigit() or int(value[0]) <= 0:
                    raise ValueError("Invalid public-registry pagination")
                pages.append(int(value[0]))
    records = []
    for position, cells in enumerate(parser.rows, 1):
        values = [cell["text"] for cell in cells]
        if not values[0] or not values[3]:
            raise ValueError("Public announcement lacks type/debtor name")
        date = pd.to_datetime(values[1], format=settings["date_format"], errors="coerce", utc=True)
        links = [urljoin(source_url, link) for link in cells[6]["links"]
                 if urlparse(urljoin(source_url, link)).scheme in ("http", "https")]
        records.append({"entity_id": None, "corporate_debtor_name": values[3],
                        "announcement_type": values[0], "announcement_date_text": values[1],
                        "period_end": date, "source_url": ";".join(links) or source_url,
                        "listing_url": source_url, "page": page, "row": position,
                        "needs_verification": 1, "is_synthetic": is_synthetic})
    return records, max(pages)


def collect_registry(config: Config, *, offline: bool) -> None:
    """Cache every linked page; this is acquisition coverage, not negative labels."""
    settings = config.section("registry_config")
    client = CachedDownloader(config)
    records, coverage = [], []
    page, expected = 1, None
    try:
        while expected is None or page <= expected:
            url = settings["url"] + (f"?page={page}" if page != 1 else "")
            filename = settings["first_filename"] if page == 1 else settings["page_filename"].format(
                page=page, snapshot=settings["snapshot_date"].replace("-", ""))
            raw = client.fetch(settings["source"], url, filename, offline=offline)
            rows, last = parse_announcements(raw.read_text(encoding="utf-8"), url, settings, page=page, is_synthetic=0)
            if expected is None:
                expected = last
            observed = pd.Timestamp(raw.stat().st_mtime, unit="s", tz="UTC")
            for row in rows:
                row.update(public_date=observed, date_is_imputed=1,
                           source_doc=raw.relative_to(config.root).as_posix())
            records.extend(rows)
            coverage.append({"page": page, "expected_pages": expected, "reported_last_page": last,
                             "rows": len(rows), "source_url": url, "source_doc": raw.relative_to(config.root).as_posix(),
                             "sha256": sha256_file(raw), "public_date": observed,
                             "needs_verification": int(last != expected), "is_synthetic": 0})
            write_real_table(pd.DataFrame(coverage), config.path("registry_pages"))
            LOG.info("Registry pages=%s/%s rows=%s; issuer/CIRP-date review pending; no survival inferred", page, expected, len(records))
            if last != expected:
                raise RuntimeError("Registry pagination changed during acquisition; snapshot completeness is unresolved")
            page += 1
    finally:
        client.close()
        if records:
            write_real_table(pd.DataFrame(records), config.path("registry_records"))
