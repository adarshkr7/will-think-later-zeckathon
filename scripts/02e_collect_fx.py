"""Cache original historical FX releases with their actual publication dates."""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.data.fx import collect_fx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    collect_fx(config, offline=args.offline)


if __name__ == "__main__":
    main()
