"""Explicit first-equity-listing certificates, used for coverage auditing only."""

from __future__ import annotations

import pandas as pd
from pypdf import PdfReader

from prahari.config import Config
from prahari.data.downloads import CachedDownloader
from prahari.data.entity_review import require_reviewed_text
from prahari.data.uci import sha256_file


def listing_rows(spec: dict, url: str, text: str, lag_days: int, *, is_synthetic: int) -> list[dict]:
    """Keep the certificate's publication separate from its historical event.

    A first observed quote is not a listing certificate. The reviewed source
    must explicitly establish the first equity listing and the named venues.
    """
    require_reviewed_text(text, [*spec["evidence_markers"], spec["listing_date_marker"]])
    listed = pd.to_datetime(spec["listing_date"], utc=True)
    if pd.to_datetime(spec["listing_date_marker"], utc=True) != listed:
        raise ValueError("Listing date disagrees with the reviewed source marker")
    report_end = pd.to_datetime(spec["source_period_end"], utc=True)
    imputed = int(not spec.get("public_date"))
    if imputed and lag_days <= 0:
        raise ValueError("Unknown listing-certificate publication needs a positive source-report lag")
    public = report_end + pd.Timedelta(days=lag_days) if imputed else pd.to_datetime(spec["public_date"], utc=True)
    if listed > report_end or public < report_end or not spec["exchanges"]:
        raise ValueError("Invalid listing certificate dates or venues")
    return [{"entity_id": spec["entity_id"], "exchange": exchange,
             "listing_date": listed.date().isoformat(), "period_end": listed.date().isoformat(),
             "public_date": public.isoformat(), "source_url": f"{url}#page={spec['page']}",
             "date_is_imputed": imputed, "needs_verification": 0, "is_synthetic": is_synthetic}
            for exchange in spec["exchanges"]]


def reviewed_listings(config: Config) -> pd.DataFrame:
    rows = []
    client = CachedDownloader(config)
    try:
        for document in config.section("source_config")["documents"]:
            spec = document.get("listing_review")
            if not spec or spec.get("reviewed") is not True:
                continue
            raw = client.fetch(document["source"], document["url"], document["filename"], offline=True)
            if sha256_file(raw) != spec["source_sha256"]:
                raise ValueError("Reviewed listing certificate bytes changed")
            text = PdfReader(raw).pages[spec["page"]-1].extract_text()
            rows.extend(listing_rows(spec, document["url"], text,
                                     config.base["dates"]["annual_report_lag_days"],
                                     is_synthetic=int(document.get("is_synthetic", 0))))
    finally:
        client.close()
    return pd.DataFrame(rows, columns=config.section("manual_config")["tables"]["listing_events"]["columns"])
