"""Deterministic extraction from individually reviewed source table mappings."""

from __future__ import annotations

from decimal import Decimal
import logging
import re
import unicodedata

import pandas as pd
from pypdf import PdfReader

from prahari.config import Config
from prahari.data.downloads import CachedDownloader
from prahari.data.uci import sha256_file

LOG = logging.getLogger(__name__)


def amount_columns(text: str, label: str, count: int, *, occurrence: int = 0,
                   expected_matches: int = 1) -> list[float | None]:
    """Read a reviewed statement row, preserving dash cells as unknown.

    Labels are compared without typography/spacing so PDF word fragments do
    not shift column positions. Ambiguity and unexpected token counts fail.
    Printed amounts are read without estimating missing components.
    """
    normalized = lambda value: re.sub("[^a-z]", "", unicodedata.normalize("NFKD", value).lower())
    matches = [line for line in text.splitlines() if normalized(line).endswith(normalized(label))]
    if len(matches) != expected_matches or not 0 <= occurrence < expected_matches:
        raise ValueError(f"Source row label is missing or ambiguous: {label}")
    line = matches[occurrence]
    last_letter = max(match.end() for match in re.finditer("[A-Za-z]", line))
    # Some PDF font runs insert whitespace immediately before a thousands comma.
    amounts_text = re.sub(r"(?<=\d)\s+(?=,\d)", "", line[last_letter:])
    tokens = re.findall(r"\(?-?\d[\d,]*(?:\.\d+)?\)?|(?<!\S)[—–-](?!\S)", amounts_text)
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


def reviewed_values(text: str, rule: str | dict, columns: int, periods: int) -> list[float | None]:
    """Read only explicitly reviewed positions, including printed interleaved subtotals.

    Old statements sometimes print each year's line item followed by its group
    subtotal. Positions select the printed subtotal; they never sum inferred data.
    Repeated labels require an exact expected count and a reviewed occurrence.
    """
    details = {"label": rule} if isinstance(rule, str) else rule
    if "sum" in details:
        components = details["sum"]
        if (not isinstance(components, list) or len(components) < 2
                or any(isinstance(component, dict) and "sum" in component for component in components)):
            raise ValueError("Reviewed sums require distinct non-nested source rows")
        labels = [component if isinstance(component, str) else component["label"] for component in components]
        if len(set(labels)) != len(labels):
            raise ValueError("Reviewed sums must not count a source row twice")
        columns_by_component = [reviewed_values(text, component, columns, periods) for component in components]
        return [None if any(value is None for value in values) else
                float(sum(Decimal(str(value)) for value in values))
                for values in zip(*columns_by_component, strict=True)]
    count = details.get("columns", columns)
    if "line_offset" in details:
        lines = text.splitlines()
        normalized = lambda value: re.sub("[^a-z]", "", unicodedata.normalize("NFKD", value).lower())
        matches = [index for index, line in enumerate(lines) if normalized(line).endswith(normalized(details["label"]))]
        expected = details.get("expected_matches", 1)
        occurrence = details.get("occurrence", 0)
        offset = details["line_offset"]
        if len(matches) != expected or not 0 <= occurrence < expected or not isinstance(offset, int) or offset <= 0:
            raise ValueError("Ambiguous reviewed subtotal anchor/offset")
        index = matches[occurrence] + offset
        if index >= len(lines) or re.fullmatch(r"[\d,().\s+\-\u2013\u2014]+", lines[index]) is None:
            raise ValueError("Reviewed subtotal line is not amount-only")
        text = details["label"] + " " + lines[index]
        details = {**details, "occurrence": 0, "expected_matches": 1}
    values = amount_columns(text, details["label"], count, occurrence=details.get("occurrence", 0),
                            expected_matches=details.get("expected_matches", 1))
    positions = details.get("positions", list(range(periods)))
    if (len(positions) != periods or len(set(positions)) != periods
            or any(not isinstance(index, int) or not 0 <= index < count for index in positions)):
        raise ValueError("Invalid reviewed financial column positions")
    return [values[index] for index in positions]


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
                markers = config.section("india_config")["financials"]["source_unit_markers"]
                marker = table.get("unit_marker", spec.get("unit_marker", markers.get(spec["unit"])))
                if not marker or marker not in re.sub("[^a-z]", "", text.lower()):
                    raise ValueError("Source table denomination changed; review required")
                for field, label in table["fields"].items():
                    periods = table.get("fiscal_periods", spec["fiscal_periods"])
                    values = reviewed_values(text, label, table["columns"], len(periods))
                    for fy_end, value in zip(periods, values, strict=True):
                        rows.append({"entity_id": spec["entity_id"], "fy_end": fy_end, "period_end": fy_end,
                                     "source_period_end": spec["source_period_end"], "basis": table["basis"],
                                     "field": field, "numeric_value": value, "text_value": None,
                                     "unit": spec["unit"], "publication_kind": "annual_report", "public_date": spec.get("public_date"),
                                     "source_doc": ";".join(filter(None, [document["url"], spec.get("publication_source_url")])), "source_page": table["page"],
                                     "date_is_imputed": int(not spec.get("public_date")), "needs_verification": int(value is None), "is_synthetic": 0})
            LOG.info("Extracted reviewed report %s; no publication date inferred from audit signing date", document["name"])
    finally:
        downloader.close()
    columns = config.section("manual_config")["tables"]["financial_evidence"]["columns"]
    return pd.DataFrame(rows, columns=columns)
