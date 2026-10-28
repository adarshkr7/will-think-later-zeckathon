"""Export a reproducible suitability audit of supplied public sources, offline."""

import argparse
import json
import logging
import sys
import zipfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from pypdf import PdfReader

from prahari.config import Config
from prahari.data.firewall import write_real_table
from prahari.data.uci import sha256_file


def verified_cache(config: Config, source: str, filename: str, receipt_suffix: str = ".zip.receipt.json") -> Path:
    path = config.path("raw") / source / filename
    # The original UCI collector predates the generic downloader's suffix.
    receipt = path.with_suffix(receipt_suffix) if receipt_suffix == ".receipt.json" else path.with_suffix(path.suffix + ".receipt.json")
    metadata = json.loads(receipt.read_text(encoding="utf-8"))
    if sha256_file(path) != metadata["sha256"] or not metadata["source_url"]:
        raise ValueError("Supplied-source cache integrity failure")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    rows = []
    for spec in config.section("supplied_sources_config")["sources"]:
        path = verified_cache(config, spec["cache_source"], spec["filename"], spec.get("receipt_suffix", "generic"))
        row = {"name": spec["name"], "source_url": spec["url"], "source_doc": path.relative_to(config.root).as_posix(),
               "sha256": sha256_file(path), "decision": spec["decision"], "reason": spec["reason"],
               "rows_inspected": None, "files": None, "columns": None, "companies": None,
               "earliest_year": None, "latest_year": None, "pages": None,
               "funding_total_equals_assets_rows": None, "funding_components_reconcile_rows": None,
               "numeric_rows_opened": 0, "license": None, "version": None,
               "needs_verification": 1 if spec["decision"] in ("discovery_only", "separate_entity_original") else 0,
               "is_synthetic": 0}
        if spec.get("metadata"):
            metadata_path = verified_cache(config, spec["cache_source"], spec["metadata"])
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            row.update(license=metadata.get("licenseName"), version=metadata.get("currentVersionNumber"))
        kind = spec["inspect"]
        if kind in ("anonymous_financial", "selected_prices", "indian_financial", "snapshot"):
            with zipfile.ZipFile(path) as archive:
                tables = [pd.read_csv(archive.open(name)) for name in archive.namelist() if name.lower().endswith(".csv")]
            row.update(rows_inspected=sum(len(table) for table in tables), files=len(tables),
                       columns=max(len(table.columns) for table in tables), numeric_rows_opened=1)
            if kind == "indian_financial":
                table = tables[0]
                row.update(companies=table.Company.nunique(), earliest_year=table.Year.min(), latest_year=table.Year.max(),
                           funding_total_equals_assets_rows=int(table["Total Liabilities"].eq(table["Total Assets"]).sum()),
                           funding_components_reconcile_rows=int(np.isclose(
                               table[["Equity Share Capital", "Reserves", "Borrowings", "Other Liabilities"]].sum(axis=1, min_count=4),
                               table["Total Liabilities"], rtol=0, atol=0.01).sum()))
        elif kind == "original_pdf":
            row["pages"] = len(PdfReader(path).pages)
        elif kind == "protected_benchmark_archive":
            # Inspect neither rows nor their membership. A receipt hash suffices.
            pass
        elif kind != "documentation":
            raise ValueError("Unknown supplied-source inspection policy")
        rows.append(row)
    table = pd.DataFrame(rows)
    write_real_table(table, config.path("supplied_source_review"))
    lines = ["# Supplied public-source review", "", "Generated from `outputs/supplied_source_review.csv`; original files and integrity receipts remain in the ignored raw cache.", "",
             "The Indian data must meet the implementation plan's identity, accounting-basis and publication-date requirements before it can enter the panel. Candidate sources do not waive those checks. Benchmark numeric rows are excluded from this review.", ""]
    for row in table.to_dict("records"):
        lines.extend([f"## {row['name']}", "", f"[{row['decision']}]({row['source_url']}). {row['reason']}", "",
                      f"Cache: `{row['source_doc']}`. SHA-256: `{row['sha256']}`.", ""])
        observed = [f"{key}: {row[key]:g}" for key in ("rows_inspected", "files", "columns", "companies", "earliest_year", "latest_year", "pages", "funding_total_equals_assets_rows", "funding_components_reconcile_rows") if pd.notna(row[key])]
        if observed:
            lines.extend(["Observed audit fields: " + "; ".join(observed) + ".", ""])
    config.path("supplied_sources_document").write_text("\n".join(lines), encoding="utf-8")
    logging.info("Supplied source audit rows=%s dates_imputed=0; no financial observations imported", len(table))


if __name__ == "__main__":
    main()
