"""Only explicitly documented equivalent ratios enter cross-country transfer."""

import pandas as pd


def harmonize(table: pd.DataFrame, source: str, mapping: dict, *, shared_only: bool) -> pd.DataFrame:
    result = {}
    for canonical, spec in mapping["ratios"].items():
        if shared_only and (not spec["polish"] or not spec["taiwan"]):
            continue
        column = spec[source]
        if column is None:
            continue
        if column not in table:
            raise ValueError(f"Unverified or missing {source} mapping: {canonical}: {column}")
        result[canonical] = pd.to_numeric(table[column], errors="raise")
    return pd.DataFrame(result, index=table.index)
