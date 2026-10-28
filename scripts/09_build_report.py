"""Generate the report and pitch outline from the offline output bundle."""

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.eval.report import build_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    build_report(config)
    logging.info("Report generated from output artifacts: %s", config.path("final_report"))


if __name__ == "__main__":
    main()
