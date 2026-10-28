"""Reject synthetic data before any production artifact is written."""

from pathlib import Path

import pandas as pd


def assert_real(table: pd.DataFrame) -> None:
    if "is_synthetic" not in table:
        raise ValueError("Missing is_synthetic provenance flag")
    if table["is_synthetic"].isna().any() or not table["is_synthetic"].eq(0).all():
        raise ValueError("Synthetic or unverified synthetic provenance in production data")


def write_real_table(table: pd.DataFrame, path: Path) -> None:
    assert_real(table)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    if path.suffix == ".parquet":
        table.to_parquet(temporary, index=False)
    elif path.suffix == ".csv":
        table.to_csv(temporary, index=False)
    else:
        raise ValueError(f"Unsupported output format: {path.suffix}")
    temporary.replace(path)
