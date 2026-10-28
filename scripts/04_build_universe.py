"""Write quarter membership from public snapshots; state the market-only fallback."""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.data.feature_inputs import load_feature_sources
from prahari.data.firewall import write_real_table
from prahari.data.universe import universe_as_of


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--date")
    parser.add_argument("--arena", choices=["P", "U"], default="P")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    settings = config.section("feature_config")["dates"]
    dates = [pd.Timestamp(args.date)] if args.date else pd.date_range(settings["first_quarter"], settings["last_quarter"], freq="QE-MAR")
    sources = load_feature_sources(config)
    for day in dates:
        table = universe_as_of(sources, config, day, args.arena)
        write_real_table(table, config.path("universe_cache") / args.arena / f"{day:%Y-%m-%d}.parquet")
        logging.info("Universe %s %s rows=%s unknown_sources=%s; financial-debt ranking unavailable when financial coverage is absent", args.arena, day.date(), len(table), table.max_source_date.isna().sum())


if __name__ == "__main__":
    main()
