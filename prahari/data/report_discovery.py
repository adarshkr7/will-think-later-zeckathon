"""Discover original annual-report links from public, unregistered document lists.

No logged-in exports, current financial tables or credentials are accessed.
Downloaded reports remain candidates until statement and publication review.
"""

from __future__ import annotations

from html.parser import HTMLParser
import json
import logging
import math
import re
from urllib.parse import quote, urljoin, urlparse

import pandas as pd
import requests

from prahari.config import Config
from prahari.data.downloads import CachedDownloader, SourceBlocked
from prahari.data.firewall import write_real_table
from prahari.data.asof import as_of
from prahari.data.filing_identity import filing_identity
from prahari.data.bhavcopy import archive_url, parse_bhavcopy
from prahari.data.manual import read_manual
from prahari.data.uci import sha256_file

LOG = logging.getLogger(__name__)


def matching_price_identities(config: Config, cutoff: pd.Timestamp, settings: dict) -> pd.DataFrame:
    """Find original pre-cutoff quote identities; absence never proves closure."""
    market_settings = config.section("india_config")["market"]
    client = CachedDownloader(config)
    try:
        for back in range(1, settings["identity_quote_lookback_days"]+1):
            day = cutoff-pd.Timedelta(days=back)
            url, filename = archive_url(day, market_settings)
            try:
                raw = client.fetch(settings["market_identity_source"], url, filename, offline=True)
            except FileNotFoundError:
                continue
            snapshot = as_of(parse_bhavcopy(raw.read_bytes(), url, market_settings), cutoff)
            snapshot = snapshot.loc[snapshot.series.eq("EQ")]
            if not snapshot.empty:
                if snapshot.symbol.duplicated().any():
                    raise ValueError("Original quote has ambiguous security identities")
                return snapshot.set_index("symbol")
    finally:
        client.close()
    return pd.DataFrame()


def prepare_peer_candidates(config: Config) -> None:
    """Source a research pool before matching; never certify sector or survival.

    Search groups and filing-index identities are investigation leads. Original
    pre-cutoff quotes corroborate identities where available; conflicts remain
    explicit. Selection still requires classification, asset and survival gates.
    """
    settings = config.section("report_discovery_config")
    identity_settings = config.section("financial_index_config")
    wanted = {symbol for group in settings["candidate_search_groups"] for symbol in group["symbols"]}
    windows = pd.read_csv(config.path("financial_index_coverage"))
    rows = []
    client = CachedDownloader(config)
    try:
        for window in windows.loc[windows.status.eq("cached_index") & windows.needs_verification.eq(0)].itertuples():
            name = config.root / window.source_doc
            raw = client.fetch(identity_settings["source"], window.source_url, name.name, offline=True)
            if sha256_file(raw) != window.sha256 or window.is_synthetic != 0:
                raise ValueError("Candidate discovery index integrity failure")
            body = json.loads(raw.read_bytes())
            filings = body.get("data") if isinstance(body, dict) else body
            for filing in filings:
                if filing.get("symbol") not in wanted:
                    continue
                identity = filing_identity(filing, {filing.get("isin")}, window.source_url, identity_settings)
                if identity is not None:
                    rows.append({**identity, "name": filing.get("companyName")})
    finally:
        client.close()
    if not rows:
        raise ValueError("No dated original identity evidence for the research pool")
    identities = pd.DataFrame(rows).drop_duplicates()
    # Multiple results for a period can share an identity and publication time.
    identities = identities.drop_duplicates(["entity_id", "period_end", "public_date", "exchange", "exchange_code"])
    cases = read_manual(config, "events").set_index("nse_symbol")
    lag = config.section("india_config")["panel"]["match_lag_quarters"]
    pool = []
    quote_cache = {}
    for group in settings["candidate_search_groups"]:
        for focal in group["cases"]:
            case = cases.loc[focal]
            cutoff = pd.to_datetime(case.event_date, utc=True)-pd.DateOffset(months=3*lag)
            # This is document acquisition from unverified index claims, never
            # feature access. These dates only restrict the search window;
            # actual identities are corroborated from as_of original quotes.
            snapshot = identities.loc[pd.to_datetime(identities.public_date, utc=True).lt(cutoff)
                                      & pd.to_datetime(identities.period_end, utc=True).lt(cutoff)].copy()
            snapshot = snapshot.loc[snapshot.exchange_code.isin(group["symbols"])]
            snapshot = snapshot.sort_values("public_date").drop_duplicates("exchange_code", keep="last")
            if cutoff not in quote_cache:
                quote_cache[cutoff] = matching_price_identities(config, cutoff, settings)
            quotes = quote_cache[cutoff]
            for row in snapshot.itertuples():
                quote = quotes.loc[row.exchange_code] if row.exchange_code in quotes.index else None
                conflict = quote is not None and quote.entity_id != row.entity_id
                pool.append({"case_entity_id": case.entity_id, "entity_id": quote.entity_id if quote is not None else row.entity_id,
                             "symbol": row.exchange_code, "filing_index_isin": row.entity_id,
                             "identity_corroboration": "filing_price_conflict" if conflict else ("original_price_agrees" if quote is not None else "no_corroborating_quote_identity"),
                             "bse_code": None, "name": row.name,
                             "period_end": (quote.period_end if quote is not None else row.period_end).date(),
                             "public_date": max(row.public_date, quote.public_date) if quote is not None else row.public_date,
                             "source_url": row.source_url+(";"+quote.source_url if quote is not None else ""),
                             "matching_cutoff": cutoff, "reason": "unreviewed_sector_assets_survival",
                             "date_is_imputed": max(row.date_is_imputed, int(quote.date_is_imputed)) if quote is not None else row.date_is_imputed,
                             "needs_verification": 1, "is_synthetic": max(row.is_synthetic, int(quote.is_synthetic)) if quote is not None else row.is_synthetic})
    client = CachedDownloader(config)
    try:
        for lead in settings.get("market_identity_leads", []):
            case = cases.loc[lead["case"]]
            cutoff = pd.to_datetime(case.event_date, utc=True)-pd.DateOffset(months=3*lag)
            market_settings = config.section("india_config")["market"]
            url, filename = archive_url(lead["day"], market_settings)
            raw = client.fetch(settings["market_identity_source"], url, filename, offline=True)
            snapshot = as_of(parse_bhavcopy(raw.read_bytes(), url, market_settings), cutoff)
            identity = snapshot.loc[snapshot.symbol.eq(lead["symbol"]) & snapshot.series.eq("EQ")]
            if len(identity) != 1:
                raise ValueError("Market research lead lacks an unambiguous original pre-cutoff identity")
            row = identity.iloc[0]
            pool.append({"case_entity_id": case.entity_id, "entity_id": row.entity_id, "symbol": row.symbol,
                         "bse_code": None, "name": None, "period_end": row.period_end.date(),
                         "public_date": row.public_date, "source_url": row.source_url,
                         "matching_cutoff": cutoff, "reason": "unreviewed_sector_assets_survival",
                         "date_is_imputed": row.date_is_imputed, "needs_verification": 1, "is_synthetic": row.is_synthetic})
    finally:
        client.close()
    for lead in settings.get("unverified_document_leads", []):
        case = cases.loc[lead["case"]]
        pool.append({"case_entity_id": case.entity_id, "entity_id": lead["entity_id"], "symbol": lead["symbol"],
                     "bse_code": lead.get("bse_code"), "name": None, "period_end": lead["period_end"],
                     "public_date": None, "source_url": lead["source_url"],
                     "matching_cutoff": pd.to_datetime(case.event_date, utc=True)-pd.DateOffset(months=3*lag),
                     "reason": lead["reason"], "date_is_imputed": 1, "needs_verification": 1, "is_synthetic": 0})
    write_real_table(pd.DataFrame(pool), config.path("peer_discovery_candidates"))
    LOG.info("Research candidate pairs=%s dates_imputed=%s; sector/assets/survival unresolved; peers unchanged", len(pool), sum(row["date_is_imputed"] for row in pool))


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


def discover_reports(config: Config, *, offline: bool, limit: int | None = None, candidates: bool = False) -> None:
    settings = config.section("report_discovery_config")
    years_before = config.section("india_config")["panel"]["collection_years_before"]
    cases, peers = read_manual(config, "events"), read_manual(config, "peers")
    windows = {row.entity_id: pd.Timestamp(row.event_date).year for row in cases.itertuples()}
    cohort = [(row.entity_id, row.nse_symbol, row.bse_code, windows[row.entity_id])
              for row in cases.loc[cases.needs_verification.eq(0)].itertuples()]
    cohort += [(row.entity_id, row.symbols, None, windows[row.matched_to])
               for row in peers.loc[peers.needs_verification.eq(0)].itertuples()]
    if candidates:
        # Research pool only. Sector, asset distance and survival are unresolved;
        # nothing here promotes a company to peer status or a model input.
        pool = pd.read_csv(config.path("peer_discovery_candidates"), dtype={"entity_id": str, "bse_code": str})
        if not pool.is_synthetic.eq(0).all() or not pool.needs_verification.eq(1).all():
            raise ValueError("Research candidates require real-source taint and unresolved eligibility")
        # Future reports support outcome/survival review only. Their later public
        # dates remain mandatory if any financial fields are imported later.
        survival_years = math.ceil(config.section("india_config")["panel"]["survival_quarters"]/4)
        years_before += survival_years
        cohort = [(row.entity_id, row.symbol, row.bse_code, windows[row.case_entity_id]+survival_years)
                  for row in pool.itertuples()]
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
