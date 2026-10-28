"""Prepare offline app files; clearly distinguish readiness from scored replay."""

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.eval.readiness import build_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    manifest = build_bundle(config)
    logging.info("Offline bundle mode=%s quarters=%s", manifest["mode"], len(manifest["quarters"]))


if __name__ == "__main__":
    main()
