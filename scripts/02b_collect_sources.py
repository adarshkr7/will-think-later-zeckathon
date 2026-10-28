"""Cache the explicitly sourced public documents; never infer company values."""

import argparse
import sys
import logging
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import requests

from prahari.config import Config
from prahari.data.downloads import CachedDownloader, SourceBlocked, SourceUnavailable
from prahari.data.firewall import write_real_table
from prahari.data.uci import sha256_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    downloader = CachedDownloader(config)
    rows = []
    try:
        for document in config.section("source_config")["documents"]:
            try:
                path = downloader.fetch(document["source"], document["url"], document["filename"], offline=args.offline)
            except SourceUnavailable:
                rows.append({"name": document["name"], "source_url": document["url"], "source_doc": None,
                             "sha256": None, "purpose": document["purpose"], "status": "unavailable_404",
                             "needs_verification": 1, "is_synthetic": 0})
                logging.warning("Original source unavailable: %s; no financial values substituted", document["name"])
                continue
            except (SourceBlocked, requests.RequestException, FileNotFoundError) as exc:
                rows.append({"name": document["name"], "source_url": document["url"], "source_doc": None,
                             "sha256": None, "purpose": document["purpose"], "status": "not_cached",
                             "needs_verification": 1, "is_synthetic": 0})
                logging.warning("Source pending: %s (%s); continuing other sources", document["name"], type(exc).__name__)
                continue
            if not path.read_bytes().startswith(b"%PDF-"):
                rows.append({"name": document["name"], "source_url": document["url"],
                             "source_doc": str(path.relative_to(config.root)).replace("\\", "/"),
                             "sha256": sha256_file(path), "purpose": document["purpose"],
                             "status": "cached_non_pdf", "needs_verification": 1, "is_synthetic": 0})
                logging.warning("Linked resource is not a PDF: %s; original response retained", document["name"])
                continue
            rows.append({"name": document["name"], "source_url": document["url"],
                         "source_doc": str(path.relative_to(config.root)).replace("\\", "/"),
                         "sha256": sha256_file(path), "purpose": document["purpose"],
                         "status": "cached",
                         "needs_verification": document.get("needs_verification", 1), "is_synthetic": 0})
        write_real_table(pd.DataFrame(rows), config.path("source_catalog"))
        if any(row["status"] in ("not_cached", "cached_non_pdf") for row in rows):
            raise SystemExit("Some original PDFs remain pending; inspect outputs/source_catalog.csv")
    finally:
        downloader.close()


if __name__ == "__main__":
    main()
