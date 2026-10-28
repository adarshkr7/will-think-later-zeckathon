"""Collect dated historical financial-filing indexes; never invent statement values."""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.data.financial_index import collect_financial_indexes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    collect_financial_indexes(config, start=args.start, end=args.end, offline=args.offline)


if __name__ == "__main__":
    main()
