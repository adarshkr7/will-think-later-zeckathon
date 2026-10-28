"""Freeze the Indian primary protocol after data acceptance, before any replay."""

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.eval.preregistration import freeze


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--amend")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    freeze(config, amend=args.amend)
    logging.info("Indian lock written; commit that file alone before replay")


if __name__ == "__main__":
    main()
