"""Verify original NSE shareholding XML and retain dated publication evidence.

Archive discovery: https://github.com/yurukatsu/nse-historical-membership .
Downloaded repository code is never executed. Numeric observations are parsed
from original exchange XML, with explicit category dimensions and denominators.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json
import logging
from urllib.parse import quote, urlencode, urlparse
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd

from prahari.config import Config
from prahari.data.downloads import CachedDownloader, SourceBlocked, SourceUnavailable
from prahari.data.firewall import write_real_table
from prahari.data.manual import read_manual

LOG = logging.getLogger(__name__)


def _local(value: str) -> str:
    return value.rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def parse_shareholding(payload: bytes, entity_id: str, period: str, public: pd.Timestamp,
                       source_url: str, publication_source: str, settings: dict) -> tuple[dict, dict]:
    """SEBI SHP: promoter %=A/(A+B+C2), pledge %=pledged/A; no missing zero.

    Counts come only from explicitly stated category totals. Depository shares
    C1 are removed from the percentage base, but remain in outstanding shares.
    Missing or zero denominators produce unknown ratios with verification flags.
    """
    if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise ValueError("Shareholding XML declarations are not permitted")
    root = ET.fromstring(payload)
    synthetic = int(root.attrib.get("is_synthetic", 0))
    tags: dict[str, set[str]] = {}
    for element in root:
        if element.text and element.text.strip():
            tags.setdefault(_local(element.tag), set()).add(element.text.strip())
    if tags.get(settings["isin_tag"]) != {entity_id}:
        raise ValueError("Original shareholding filing identity differs from the requested security")
    day = pd.Timestamp(period).date().isoformat()
    if tags.get(settings["report_date_tag"]) != {day}:
        raise ValueError("Original shareholding filing period differs from its index")
    if public.tzinfo is None or public < pd.Timestamp(day, tz="UTC"):
        raise ValueError("Invalid original shareholding publication timestamp")
    context_members = {}
    namespace = settings["xbrl_namespace"]
    dimensions = settings["dimensions_namespace"]
    for context in root.findall(f"{{{namespace}}}context"):
        members = context.findall(f".//{{{dimensions}}}explicitMember")
        instant = context.find(f"{{{namespace}}}period/{{{namespace}}}instant")
        if (len(members) == 1 and instant is not None and instant.text == day
                and _local(members[0].attrib.get("dimension", "")) == settings["category_axis"]):
            context_members[context.attrib["id"]] = _local(members[0].text or "")
    facts: dict[tuple[str, str], set[Decimal]] = {}
    wanted = {settings["shares_tag"], *settings["pledged_tags"]}
    for element in root:
        member = context_members.get(element.attrib.get("contextRef"))
        tag = _local(element.tag)
        if member is None or tag not in wanted or not (element.text or "").strip():
            continue
        try:
            value = Decimal(element.text.strip())
        except InvalidOperation as exc:
            raise ValueError("Non-numeric original shareholding count") from exc
        if not value.is_finite() or value < 0 or value != value.to_integral_value():
            raise ValueError("Shareholding counts must be finite non-negative integers")
        facts.setdefault((member, tag), set()).add(value)
    if any(len(values) != 1 for values in facts.values()):
        raise ValueError("Conflicting original shareholding category counts")
    def count(member: str, names: list[str]) -> float:
        values = {next(iter(facts[(member, name)])) for name in names if (member, name) in facts}
        if len(values) > 1:
            raise ValueError("Conflicting original pledge measures")
        return float(next(iter(values))) if values else np.nan
    total = count(settings["total_member"], [settings["shares_tag"]])
    promoter = count(settings["promoter_member"], [settings["shares_tag"]])
    dr = count(settings["dr_member"], [settings["shares_tag"]])
    pledged = count(settings["promoter_member"], settings["pledged_tags"])
    if np.isfinite(total) and ((np.isfinite(promoter) and promoter > total) or (np.isfinite(dr) and dr > total)):
        raise ValueError("Shareholding subtotals exceed stated outstanding shares")
    if np.isfinite(promoter) and np.isfinite(pledged) and pledged > promoter:
        raise ValueError("Pledged shares exceed the promoter's shares")
    base = total-dr
    holding = settings["percentage_scale"]*promoter/base if np.isfinite(base) and base > 0 else np.nan
    pledge = settings["percentage_scale"]*pledged/promoter if np.isfinite(promoter) and promoter > 0 else np.nan
    common = {"entity_id": entity_id, "period_end": day, "public_date": public.isoformat(),
              "date_is_imputed": 0, "is_synthetic": synthetic}
    provenance = source_url+";"+publication_source
    shares = {**common, "shares_outstanding": total if total > 0 else np.nan, "source_doc": provenance,
              "needs_verification": int(not np.isfinite(total) or total <= 0)}
    holding_row = {**common, "promoter_holding_pct": holding, "promoter_pledged_pct_of_promoter": pledge,
                   "source_url": provenance, "needs_verification": int(not np.isfinite(holding) or not np.isfinite(pledge))}
    return shares, holding_row


def _merge_manual(config: Config, name: str, rows: list[dict]) -> None:
    if not rows:
        return
    existing = read_manual(config, name)
    current = pd.DataFrame(rows).reindex(columns=existing.columns)
    combined = pd.concat([existing, current], ignore_index=True).drop_duplicates()
    if combined.duplicated(["entity_id", "period_end", "public_date"]).any():
        raise ValueError(f"Conflicting {name} observations; no manual data overwritten")
    write_real_table(combined, config.path("manual") / (name+".csv"))


def collect_shareholding(config: Config, *, offline: bool, limit: int | None = None) -> None:
    settings = config.section("shareholding_config")
    dates = config.section("feature_config")["dates"]
    first, last = pd.Timestamp(dates["first_quarter"], tz="UTC"), pd.Timestamp(dates["last_quarter"], tz="UTC")
    cases = read_manual(config, "events")
    peers = read_manual(config, "peers")
    windows = {row.entity_id: pd.to_datetime(row.event_date, utc=True) for row in cases.itertuples()}
    cohort = [(row.entity_id, row.nse_symbol, windows[row.entity_id]) for row in cases.loc[cases.needs_verification.eq(0)].itertuples()]
    cohort += [(row.entity_id, row.symbols, windows.get(row.matched_to, last)) for row in peers.loc[peers.needs_verification.eq(0)].itertuples()]
    downloader = CachedDownloader(config)
    audit, shares, holdings = [], [], []
    downloaded = 0
    try:
        for entity, symbol, event in sorted(set(cohort)):
            end = min(last, event) if settings["pre_event_only"] else last
            filings: dict[str, dict] = {}
            index_urls = [("archive", settings["archive_source"], settings["archive_index_url"].format(symbol=quote(symbol, safe="")),
                           settings["archive_filename"].format(entity_id=entity)),
                          ("live", settings["live_index_source"], settings["live_index_url"]+"?"+urlencode({"index": "equities", "symbol": symbol}),
                           settings["index_filename"].format(entity_id=entity, snapshot_date=settings["snapshot_date"]))]
            for kind, source, url, filename in index_urls:
                try:
                    # Reuse an earlier manually named cache of this exact URL.
                    for receipt in (config.path("raw") / source).glob("*.receipt.json"):
                        if json.loads(receipt.read_text(encoding="utf-8"))["source_url"] == url:
                            filename = receipt.name.removesuffix(".receipt.json")
                            break
                    path = downloader.fetch(source, url, filename, offline=offline)
                    body = json.loads(path.read_bytes())
                    records = body["filings"] if kind == "archive" else body
                    if not isinstance(records, list):
                        raise ValueError("Unrecognized NSE shareholding index response")
                    for row in records:
                        xml = row.get("xbrl")
                        broadcast = row.get("broadcast_date" if kind == "archive" else "broadcastDate")
                        if not xml or urlparse(xml).hostname != "nsearchives.nseindia.com" or not xml.endswith(".xml") or not broadcast:
                            continue
                        public = pd.to_datetime(broadcast, format="%d-%b-%Y %H:%M:%S").tz_localize(settings["timezone"]).tz_convert("UTC")
                        period = pd.to_datetime(row["date"], format="%d-%b-%Y", utc=True)
                        if xml in filings:
                            if public != filings[xml]["public"] or period != filings[xml]["period"]:
                                filings[xml]["date_conflict"] = True
                            elif kind == "live":
                                filings[xml]["publication_source"] = url
                        else:
                            filings[xml] = {"public": public, "period": period, "publication_source": url, "date_conflict": False}
                except SourceBlocked:
                    raise
                except (FileNotFoundError, ValueError) as exc:
                    LOG.warning("Shareholding index unavailable %s %s: %s", entity, kind, type(exc).__name__)
            for xml, row in sorted(filings.items(), key=lambda pair: (pair[1]["period"], pair[1]["public"])):
                if row["period"] < first or row["public"] >= end:
                    continue
                if limit is not None and downloaded >= limit:
                    break
                record = {"entity_id": entity, "symbol": symbol, "period_end": row["period"].date(),
                          "public_date": row["public"], "source_url": xml, "publication_source": row["publication_source"], "is_synthetic": 0}
                try:
                    if row["date_conflict"]:
                        raise ValueError("Archive and live publication timestamps disagree")
                    raw = downloader.fetch(settings["xml_source"], xml, xml.rsplit("/", 1)[-1], offline=offline)
                    share, holding = parse_shareholding(raw.read_bytes(), entity, str(row["period"].date()), row["public"], xml, row["publication_source"], settings)
                    shares.append(share)
                    holdings.append(holding)
                    downloaded += 1
                    record.update(status="verified_original" if not share["needs_verification"] and not holding["needs_verification"] else "partial_original", reason="", needs_verification=max(share["needs_verification"], holding["needs_verification"]))
                except SourceBlocked:
                    raise
                except (FileNotFoundError, ValueError, ET.ParseError) as exc:
                    record.update(status="unavailable", reason=str(exc), needs_verification=1)
                    LOG.warning("Shareholding source unavailable %s: %s", entity, type(exc).__name__)
                audit.append(record)
                LOG.info("Shareholding %s %s status=%s dates_imputed=0", entity, row["period"].date(), record["status"])
            if limit is not None and downloaded >= limit:
                break
    finally:
        downloader.close()
        _merge_manual(config, "share_counts", shares)
        _merge_manual(config, "shareholding", holdings)
        if audit:
            write_real_table(pd.DataFrame(audit), config.path("shareholding_import_review"))
