"""Initialize panel templates or validate human inputs; empty panels fail acceptance."""

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.data.firewall import write_real_table
from prahari.data.quality import initialize_templates, validate_manual


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--init-templates", action="store_true")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    if args.init_templates:
        initialize_templates(config)
        return
    summary = validate_manual(config)
    write_real_table(summary, config.path("manual_validation"))
    settings = config.section("manual_config")["validation"]
    counts = summary.set_index("table")["verified"]
    if counts["events"] < settings["minimum_events"] or counts["peers"] < settings["minimum_peers"]:
        raise SystemExit("Panel acceptance incomplete: supply verified events/peers listed in DATA_REQUESTS.md")
    logging.info("Manual schema/count checks passed; market coverage and parity acceptance still required")


if __name__ == "__main__":
    main()
