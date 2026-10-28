"""Run a registered primary replay; the lock must already have its own commit."""

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.eval.replay import replay


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--arena", choices=["P", "U"], default="P")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    result = replay(config, args.arena)
    logging.info("Registered replay rows=%s unavailable_scores=%s", len(result), result.pd_4q.isna().sum())


if __name__ == "__main__":
    main()
