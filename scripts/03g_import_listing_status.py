"""Import reviewed listing certificates without inventing pre-listing quotes."""

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from prahari.config import Config
from prahari.data.firewall import write_real_table
from prahari.data.listings import reviewed_listings
from prahari.data.quality import validate_table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    if config.path("preregistration_lock").exists():
        raise RuntimeError("Listing inputs are registered; amendment required")
    fresh = reviewed_listings(config)
    target = config.path("manual") / "listing_events.csv"
    current = pd.read_csv(target) if target.exists() else fresh.iloc[:0]
    result = pd.concat([current, fresh], ignore_index=True).drop_duplicates()
    if result.duplicated(["entity_id", "exchange", "period_end", "public_date"]).any():
        raise ValueError("Conflicting listing certificates; no existing inputs overwritten")
    validate_table(result, "listing_events", config.section("manual_config"))
    write_real_table(result, target)
    logging.info("Listing certificates rows=%s dates_imputed=%s missing=%s", len(result),
                 result.date_is_imputed.sum(), result.isna().sum().loc[lambda x: x.gt(0)].to_dict())


if __name__ == "__main__":
    main()
