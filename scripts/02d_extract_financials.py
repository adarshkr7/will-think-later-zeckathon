"""Extract configured, source-reviewed statement rows without replacing human inputs."""

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from prahari.config import Config
from prahari.data.firewall import write_real_table
from prahari.data.report_extract import extract_reviewed_reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    fresh = extract_reviewed_reports(config)
    path = config.path("manual") / "financial_evidence.csv"
    current = pd.read_csv(path)
    keys = ["entity_id", "fy_end", "basis", "field", "source_doc", "source_page"]
    combined = pd.concat([current, fresh], ignore_index=True).drop_duplicates(keep="first")
    if combined.duplicated(keys).any():
        raise ValueError("Extraction conflicts with existing field evidence; no human data overwritten")
    write_real_table(combined, path)
    logging.info("Financial evidence rows=%s dates_imputed=%s missing=%s", len(combined),
                 combined.date_is_imputed.sum(), combined.numeric_value.isna().sum())


if __name__ == "__main__":
    main()
