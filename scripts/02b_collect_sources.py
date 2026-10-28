"""Cache the explicitly sourced public documents; never infer company values."""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from prahari.config import Config
from prahari.data.downloads import CachedDownloader
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
            path = downloader.fetch(document["source"], document["url"], document["filename"], offline=args.offline)
            if not path.read_bytes().startswith(b"%PDF-"):
                raise ValueError(f"Source returned something other than a PDF: {document['name']}")
            rows.append({"name": document["name"], "source_url": document["url"],
                         "source_doc": str(path.relative_to(config.root)).replace("\\", "/"),
                         "sha256": sha256_file(path), "purpose": document["purpose"],
                         "needs_verification": 1, "is_synthetic": 0})
            write_real_table(pd.DataFrame(rows), config.path("source_catalog"))
    finally:
        downloader.close()


if __name__ == "__main__":
    main()
