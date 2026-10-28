"""Cache case/peer original annual reports from public document links."""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.data.report_discovery import discover_reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    config = Config(args.config)
    config.setup_logging()
    discover_reports(config, offline=args.offline, limit=args.limit)


if __name__ == "__main__":
    main()
