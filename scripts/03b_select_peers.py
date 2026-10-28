"""Select peers using sourced assets, classifications and survival evidence."""

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.data.firewall import write_real_table
from prahari.eval.panel_selection import manual_peer_rows, select_panel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--write-peers", action="store_true", help="Publish validated selection into the manual peer CSV")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    if config.path("preregistration_lock").exists():
        raise RuntimeError("Peer membership is registered; changes require an explicit amendment")
    selected = select_panel(config)
    write_real_table(selected, config.path("selected_peers"))
    if args.write_peers:
        write_real_table(manual_peer_rows(selected, config), config.path("manual") / "peers.csv")
    logging.info("Peer selection rows=%s dates_imputed=%s missing=%s", len(selected),
                 selected.date_is_imputed.sum(), selected.isna().sum().loc[lambda s: s.gt(0)].to_dict())


if __name__ == "__main__":
    main()
