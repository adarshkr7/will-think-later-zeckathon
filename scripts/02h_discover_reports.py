"""Cache case/peer original annual reports from public document links."""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.data.report_discovery import discover_reports, prepare_peer_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--candidates", action="store_true", help="Acquire unselected research candidates; this never writes peers.csv")
    parser.add_argument("--prepare-candidates", action="store_true", help="Prepare an unresolved research pool from cached dated identities")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    config = Config(args.config)
    config.setup_logging()
    if args.prepare_candidates:
        prepare_peer_candidates(config)
        if not args.candidates:
            return
    discover_reports(config, offline=args.offline, limit=args.limit, candidates=args.candidates)


if __name__ == "__main__":
    main()
