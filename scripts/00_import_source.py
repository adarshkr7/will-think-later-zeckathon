"""Register a human-downloaded original file with its exact public provenance."""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.data.downloads import CachedDownloader


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--source", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--filename", required=True)
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    downloader = CachedDownloader(config)
    try:
        downloader.register_manual(args.source, args.url, args.filename, args.file)
    finally:
        downloader.close()


if __name__ == "__main__":
    main()
