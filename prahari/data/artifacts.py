"""Read derived artifacts through explicit paths and verify their source cutoffs."""

from __future__ import annotations

import json

import joblib
import pandas as pd

from prahari.config import Config
from prahari.data.firewall import assert_real


def read_features(config: Config, day: str, arena: str) -> pd.DataFrame:
    cutoff = pd.to_datetime(day, utc=True)
    table = pd.read_parquet(config.path("feature_cache") / arena / f"{cutoff:%Y-%m-%d}.parquet")
    assert_real(table)
    table["max_source_date"] = pd.to_datetime(table.max_source_date, utc=True)
    if table.max_source_date.dropna().ge(cutoff).any() or not pd.to_datetime(table.scoring_date, utc=True).eq(cutoff).all():
        raise ValueError("Feature artifact cutoff or provenance mismatch")
    table.attrs["as_of"] = cutoff.isoformat()
    return table


def load_hdm_models(config: Config) -> dict:
    entries = json.loads(config.path("benchmark_model_manifest").read_text(encoding="utf-8"))
    selected = [entry for entry in entries if entry["representation"] == "harmonized" and entry["variant"] == "none"]
    result = {}
    for entry in selected:
        if entry["horizon_quarters"] not in (4, 8):
            continue
        path = config.root / entry["artifact"]
        model = joblib.load(path)
        if model.source != entry["dataset"] or config.section("benchmark_config")["datasets"][model.source]["source"] != "polish":
            raise ValueError("Primary HDM must be trained on Polish labels only")
        result[f"{entry['horizon_quarters']}q"] = model
    if set(result) != {"4q", "8q"}:
        raise ValueError("Both Polish-trained HDM horizons are required")
    return result
