"""Run only implemented pipeline phases, in configured order."""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    logging.info("Running implemented phases only; later project acceptance remains pending")
    for module in config.base["pipeline"]["modules"]:
        command = [sys.executable, "-m", module, "--config", str(config.file)]
        if args.offline:
            command.append("--offline")
        if args.prepare_only:
            command.append("--prepare-only")
        subprocess.run(command, cwd=config.root, check=True)


if __name__ == "__main__":
    main()
