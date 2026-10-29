"""Extract explicitly reviewed business classifications with dated identity proof."""

from __future__ import annotations

import logging
import re

import pandas as pd
from pypdf import PdfReader

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.downloads import CachedDownloader
from prahari.data.manual import read_manual
from prahari.data.uci import sha256_file

LOG = logging.getLogger(__name__)


def merge_reviewed_entities(current: pd.DataFrame, fresh: pd.DataFrame) -> pd.DataFrame:
    """Append earlier proven metadata while preserving existing equivalent rows.

    Another identity source can support the same classification at the same
    instant. Retain and augment the existing provenance; changed company
    classifications or symbols at an identical key require an explicit review.
    """
    keys = ["entity_id", "period_end", "public_date"]
    content = ["name", "symbols", "sector", "is_financial", "needs_verification", "is_synthetic"]
    joined = pd.concat([current, fresh], ignore_index=True)
    for _, versions in joined.groupby(keys, dropna=False):
        if len(versions[content].drop_duplicates()) > 1:
            raise ValueError("Classification conflicts with existing metadata; no human inputs replaced")
    result = joined.drop_duplicates(keys, keep="first").copy()
    sources = joined.groupby(keys, dropna=False).source_url.agg(
        lambda values: ";".join(dict.fromkeys(part for value in values for part in value.split(";") if part)))
    result["source_url"] = [sources.loc[tuple(row)] for row in result[keys].itertuples(index=False, name=None)]
    return result


def require_reviewed_text(text: str, markers: list[str]) -> None:
    """Typography normalization only; every reviewed literal must be present."""
    normalize = lambda value: re.sub(r"[^a-z0-9]", "", value.lower())
    if not markers or any(normalize(marker) not in normalize(text) for marker in markers):
        raise ValueError("Reviewed company-profile text changed or is missing")


def reviewed_entities(config: Config, t: str | pd.Timestamp) -> pd.DataFrame:
    """Retain source/profile and identity publication dates, never backfill history.

    Sector names are declared normalization choices in the reviewed source
    config. They are not inferred from company names or from outcome labels.
    """
    identities = as_of(read_manual(config, "security_crosswalk"), t)
    identities = identities.loc[identities.exchange.eq("nse")]
    client = CachedDownloader(config)
    rows = []
    try:
        for document in config.section("source_config")["documents"]:
            spec = document.get("classification_review")
            if not spec or spec.get("reviewed") is not True:
                continue
            path = client.fetch(document["source"], document["url"], document["filename"], offline=True)
            if sha256_file(path) != spec["source_sha256"]:
                raise ValueError("Reviewed classification source bytes changed")
            text = PdfReader(path).pages[spec["page"] - 1].extract_text()
            require_reviewed_text(text, spec["evidence_markers"])
            identity = identities.loc[identities.entity_id.eq(spec["entity_id"])].sort_values("public_date")
            if identity.empty:
                raise ValueError("Classification lacks a dated, sourced NSE identity")
            end = pd.to_datetime(spec["period_end"], utc=True)
            imputed = int(not spec.get("public_date"))
            publication = (end + pd.Timedelta(days=config.base["dates"]["annual_report_lag_days"])) if imputed else pd.to_datetime(spec["public_date"], utc=True)
            publication = max(publication, identity.public_date.iloc[0])
            # Symbols change. Choose the latest observed mapping available by
            # this profile's publication, not the firm's first-ever ticker.
            identity = identity.loc[identity.public_date.le(publication)].sort_values(["period_end", "public_date"]).iloc[-1]
            rows.append({"entity_id": spec["entity_id"], "name": spec["name"], "symbols": identity.exchange_code,
                         "sector": spec["sector"], "is_financial": spec["is_financial"], "period_end": end,
                         "public_date": publication, "source_url": f"{document['url']}#page={spec['page']};{identity.source_url}",
                         "date_is_imputed": max(imputed, int(identity.date_is_imputed)),
                         "needs_verification": 0, "is_synthetic": 0})
    finally:
        client.close()
    result = pd.DataFrame(rows, columns=config.section("manual_config")["tables"]["entities"]["columns"])
    LOG.info("Reviewed classifications=%s dates_imputed=%s missing=%s", len(result),
             result.date_is_imputed.sum(), result.isna().sum().loc[lambda values: values.gt(0)].to_dict())
    return as_of(result, t).drop(columns="max_source_date")
