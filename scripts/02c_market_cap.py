"""Build market-cap observations from prices and publicly available share counts."""

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.data.bhavcopy import market_as_of
from prahari.data.shareholding import share_counts_as_of
from prahari.data.firewall import write_real_table
from prahari.data.market_cap import market_cap


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    table = market_cap(market_as_of(config, args.as_of), share_counts_as_of(config, args.as_of),
                       config.section("india_config")["market"])
    write_real_table(table, config.path("market_cap"))
    logging.info("Market cap rows=%s dates_imputed=%s missing_share_counts=%s", len(table),
                 table.date_is_imputed.sum(), table.market_cap.isna().sum())


if __name__ == "__main__":
    main()
