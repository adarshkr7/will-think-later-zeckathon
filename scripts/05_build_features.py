"""Build point-in-time quarter features; unknown fields are retained with reasons."""

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
from prahari.features.panel import build_features


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
    coverage = []
    for day in dates:
        table = build_features(config, day, args.arena, sources=sources)
        write_real_table(table, config.path("feature_cache") / args.arena / f"{day:%Y-%m-%d}.parquet")
        reasons = [name for name in table if name.endswith("__reason")]
        for column in reasons:
            coverage.append({"arena": args.arena, "quarter": day.date(), "feature": column.removesuffix("__reason"),
                             "rows": len(table), "available": int(table[column].eq("").sum()),
                             "needs_verification": int(table[column].ne("").any()), "is_synthetic": 0})
        logging.info("Features %s %s rows=%s unknown_fields=%s", args.arena, day.date(), len(table), sum(int(table[column].ne("").sum()) for column in reasons))
    current = pd.DataFrame(coverage)
    target = config.path("feature_coverage")
    if target.exists():
        previous = pd.read_csv(target)
        current = pd.concat([previous, current], ignore_index=True)
        current["quarter"] = current.quarter.astype(str)
        current = current.drop_duplicates(["arena", "quarter", "feature"], keep="last")
    write_real_table(current, target)


if __name__ == "__main__":
    main()
