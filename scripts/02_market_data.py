"""Cache official historical market sessions; repeated exchange blocks stop the run."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from prahari.config import Config
from prahari.data.bhavcopy import cache_session, parse_index
from prahari.data.bse import cache_bse_session
from prahari.data.downloads import CachedDownloader, SourceBlocked, SourceUnavailable
from prahari.data.firewall import write_real_table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--exchange", choices=["auto", "nse", "bse"], default="auto")
    parser.add_argument("--import-file", type=Path)
    parser.add_argument("--import-url")
    parser.add_argument("--import-source", choices=["nse", "nse_index", "bse"])
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    settings = config.section("india_config")["market"]
    dates = settings["sample_dates"] if args.sample else pd.date_range(
        args.start or settings["start_date"], args.end or settings["end_date"], freq="B").strftime("%Y-%m-%d")
    downloader = CachedDownloader(config)
    try:
        if args.import_file:
            if not args.import_url or not args.import_source:
                parser.error("Manual import requires --import-url and --import-source")
            downloader.register_manual(args.import_source, args.import_url,
                                       args.import_url.rsplit("/", 1)[-1], args.import_file)
            return
        for day in dates:
            try:
                if args.exchange == "bse":
                    cache_bse_session(config, downloader, str(day), offline=args.offline)
                else:
                    try:
                        cache_session(config, downloader, str(day), offline=args.offline)
                    except (SourceUnavailable, SourceBlocked):
                        if args.exchange != "auto":
                            raise
                        logging.warning("NSE source unavailable; trying BSE fallback for %s", day)
                        cache_bse_session(config, downloader, str(day), offline=args.offline)
            except SourceUnavailable:
                logging.warning("Official archives unavailable for %s; unknown gap, not a proven holiday", day)
                continue
            except FileNotFoundError:
                if args.offline:
                    raise
                logging.warning("No official bhavcopy for %s; may be a holiday; no observations invented", day)
                continue
            date = pd.Timestamp(day)
            url = settings["index_url"].format(date=date.strftime("%d%m%Y"))
            try:
                raw = downloader.fetch("nse_index", url, url.rsplit("/", 1)[-1], offline=args.offline)
                table = parse_index(raw.read_bytes(), url, settings)
                if not table.period_end.eq(pd.to_datetime(day, utc=True)).all():
                    raise ValueError("Index archive observations do not match requested date")
                write_real_table(table, config.path("market_cache") / f"index_{date:%Y%m%d}.parquet")
            except FileNotFoundError:
                if args.offline:
                    raise
                logging.warning("Index unavailable for %s; not treating it as zero return", day)
    finally:
        downloader.close()


if __name__ == "__main__":
    main()
