"""Manual input access; sealed directories are never enumerated."""

from __future__ import annotations

import logging

import pandas as pd

from prahari.config import Config

LOG = logging.getLogger(__name__)


def read_manual(config: Config, name: str) -> pd.DataFrame:
    specs = config.section("manual_config")["tables"]
    if name not in specs:
        raise ValueError(f"Unknown manual table: {name}")
    table = pd.read_csv(config.path("manual") / f"{name}.csv", dtype=str)
    if set(table) != set(specs[name]["columns"]):
        raise ValueError(f"Invalid manual header: {name}")
    for column in specs[name]["flags"] + specs[name]["numeric"]:
        table[column] = pd.to_numeric(table[column], errors="raise")
    if not table.is_synthetic.eq(0).all():
        raise ValueError("Synthetic manual inputs are forbidden")
    LOG.info("%s rows=%s dates_imputed=%s missing=%s", name, len(table),
             table.date_is_imputed.sum(), table.isna().sum().loc[lambda s: s.gt(0)].to_dict())
    return table
