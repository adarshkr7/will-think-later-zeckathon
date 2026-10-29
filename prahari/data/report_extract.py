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


def reviewed_table_text(reader: PdfReader, table: dict) -> tuple[str, list[int]]:
    """Keep numeric pages separate from required contextual source assertions.

    Context pages support scope without introducing unrelated numeric rows into
    the column parser. All pages remain in the resulting evidence chain.
    """
    pages = [table["page"], *table.get("additional_pages", [])]
    context_pages = table.get("context_pages", [])
    all_pages = [*pages, *context_pages]
    if (len(set(all_pages)) != len(all_pages) or
            any(not isinstance(page, int) or not 1 <= page <= len(reader.pages) for page in all_pages)):
        raise ValueError("Invalid reviewed statement pages")
    if context_pages:
        markers = table.get("context_markers")
        if (not isinstance(markers, list) or not markers or
                any(not isinstance(marker, str) or not marker.strip() for marker in markers)):
            raise ValueError("Context pages require explicit source assertions")
        normalize = lambda value: " ".join(unicodedata.normalize("NFKC", value).casefold().split())
        context = normalize("\n".join(reader.pages[page-1].extract_text() for page in context_pages))
        if any(normalize(marker) not in context for marker in markers):
            raise ValueError("Required source assertion changed; review required")
    elif table.get("context_markers"):
        raise ValueError("Source assertions require explicit context pages")
    return "\n".join(reader.pages[page-1].extract_text(extraction_mode=table.get("text_mode", "plain"))
                     for page in pages), all_pages


def require_denomination(text: str, spec: dict, table: dict, markers: dict) -> None:
    """Check reviewed printed units, including a literal rupee symbol for INR.

    A literal marker is opt-in for a hash-pinned, visually reviewed statement;
    it must not be inferred from the numerical scale of its amounts.
    """
    literal = table.get("unit_marker_literal", spec.get("unit_marker_literal"))
    if literal is not None:
        if not isinstance(literal, str) or not literal.strip() or literal not in text:
            raise ValueError("Source table denomination changed; review required")
        return
    marker = table.get("unit_marker", spec.get("unit_marker", markers.get(spec["unit"])))
    if not marker or marker not in re.sub("[^a-z]", "", text.lower()):
        raise ValueError("Source table denomination changed; review required")


def join_spaced_thousands(text: str) -> str:
    """Join reviewed single-space thousands groups, preserving column gaps.

    This is opt-in for hash-pinned layout text whose amount columns are
    separated by multiple spaces. It must not be applied to arbitrary tables.
    """
    return re.sub(r"(?<=\d) (?=\d{3}(?:\D|$))", "", text)


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
    if "difference" in details:
        operands = details["difference"]
        if set(details) != {"difference"} or not isinstance(operands, list) or len(operands) != 2:
            raise ValueError("Reviewed differences require exactly two source operands")
        left, right = [reviewed_values(text, operand, columns, periods) for operand in operands]
        return [None if a is None or b is None else float(Decimal(str(a))-Decimal(str(b)))
                for a, b in zip(left, right, strict=True)]
    if "sum" in details:
        components = details["sum"]
        if (set(details) != {"sum"} or not isinstance(components, list) or len(components) < 2
                or any(isinstance(component, dict) and ("sum" in component or "difference" in component) for component in components)):
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
                text, pages = reviewed_table_text(reader, table)
                if table.get("spaced_thousands"):
                    if table.get("text_mode") != "layout":
                        raise ValueError("Space-grouped amounts require reviewed layout extraction")
                    text = join_spaced_thousands(text)
                markers = config.section("india_config")["financials"]["source_unit_markers"]
                require_denomination(text, spec, table, markers)
                source = document["url"]
                if len(pages) > 1:
                    source = ";".join(f"{source}#page={page}" for page in pages)
                for field, label in table["fields"].items():
                    periods = table.get("fiscal_periods", spec["fiscal_periods"])
                    values = reviewed_values(text, label, table["columns"], len(periods))
                    for fy_end, value in zip(periods, values, strict=True):
                        rows.append({"entity_id": spec["entity_id"], "fy_end": fy_end, "period_end": fy_end,
                                     "source_period_end": spec["source_period_end"], "basis": table["basis"],
                                     "field": field, "numeric_value": value, "text_value": None,
                                     "unit": spec["unit"], "publication_kind": "annual_report", "public_date": spec.get("public_date"),
                                     "source_doc": ";".join(filter(None, [source, spec.get("publication_source_url")])), "source_page": table["page"],
                                     "date_is_imputed": int(not spec.get("public_date")), "needs_verification": int(value is None), "is_synthetic": 0})
            LOG.info("Extracted reviewed report %s; no publication date inferred from audit signing date", document["name"])
    finally:
        downloader.close()
    columns = config.section("manual_config")["tables"]["financial_evidence"]["columns"]
    return pd.DataFrame(rows, columns=columns)
