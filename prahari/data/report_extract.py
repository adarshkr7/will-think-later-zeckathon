"""Deterministic extraction from individually reviewed source table mappings."""

from __future__ import annotations

from decimal import Decimal
import logging
import re

import pandas as pd
from pypdf import PdfReader

from prahari.config import Config
from prahari.data.downloads import CachedDownloader
from prahari.data.uci import sha256_file

LOG = logging.getLogger(__name__)


def amount_columns(text: str, label: str, count: int) -> list[float | None]:
    """Read a reviewed statement row, preserving dash cells as unknown.

    Labels are compared without typography/spacing so PDF word fragments do
    not shift column positions. Ambiguity and unexpected token counts fail.
    No arithmetic synthesizes financial statement inputs here.
    """
    normalized = lambda value: re.sub("[^a-z]", "", value.lower())
    matches = [line for line in text.splitlines() if normalized(line).endswith(normalized(label))]
    if len(matches) != 1:
        raise ValueError(f"Source row label is missing or ambiguous: {label}")
    line = matches[0]
    last_letter = max(match.end() for match in re.finditer("[A-Za-z]", line))
    tokens = re.findall(r"\(?-?\d[\d,]*(?:\.\d+)?\)?|(?<!\S)[—–-](?!\S)", line[last_letter:])
    if len(tokens) not in (count, count + 1):
        raise ValueError(f"Unexpected amount columns for {label}: {len(tokens)}")
    amounts = []
    for token in tokens[-count:]:
        if token in ("-", "—", "–"):
            amounts.append(None)
        else:
            amount = Decimal(token.replace(",", "").strip("()"))
            amounts.append(float(-amount if token.startswith("(") else amount))
    return amounts


def extract_reviewed_reports(config: Config) -> pd.DataFrame:
    rows = []
    downloader = CachedDownloader(config)
    try:
        for document in config.section("source_config")["documents"]:
            spec = document.get("financial_extraction")
            if not spec or spec.get("reviewed") is not True:
                continue
            raw = downloader.fetch(document["source"], document["url"], document["filename"], offline=True)
            if sha256_file(raw) != spec["source_sha256"]:
                raise ValueError("Reviewed financial report bytes changed; source review required")
            reader = PdfReader(raw)
            for table in spec["tables"]:
                text = reader.pages[table["page"] - 1].extract_text()
                if "incrore" not in re.sub("[^a-z]", "", text.lower()) or spec["unit"] != "INR_crore":
                    raise ValueError("Source table denomination changed; review required")
                for field, label in table["fields"].items():
                    values = amount_columns(text, label, table["columns"])
                    for fy_end, value in zip(spec["fiscal_periods"], values, strict=False):
                        rows.append({"entity_id": spec["entity_id"], "fy_end": fy_end, "period_end": fy_end,
                                     "source_period_end": spec["source_period_end"], "basis": table["basis"],
                                     "field": field, "numeric_value": value, "text_value": None,
                                     "unit": spec["unit"], "publication_kind": "annual_report", "public_date": None,
                                     "source_doc": document["url"], "source_page": table["page"],
                                     "date_is_imputed": 1, "needs_verification": int(value is None), "is_synthetic": 0})
            LOG.info("Extracted reviewed report %s; no publication date inferred from audit signing date", document["name"])
    finally:
        downloader.close()
    columns = config.section("manual_config")["tables"]["financial_evidence"]["columns"]
    return pd.DataFrame(rows, columns=columns)
