"""Reconcile explicitly sourced internal identity keys before registration."""

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.data.identity import apply_identity_aliases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    result = apply_identity_aliases(config)
    logging.info("Identity resolutions=%s dates_imputed=%s missing=%s", len(result),
                 result.date_is_imputed.sum(), result.isna().sum().loc[lambda values: values.gt(0)].to_dict())


if __name__ == "__main__":
    main()
