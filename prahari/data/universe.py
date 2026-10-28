"""Historical public membership and explicitly declared market-only fallback."""

from __future__ import annotations

import pandas as pd

from prahari.config import Config
from prahari.data.feature_inputs import FeatureSources


def universe_as_of(sources: FeatureSources, config: Config, t: str | pd.Timestamp, arena: str) -> pd.DataFrame:
    table, _ = sources.snapshot(config, t, arena)
    fields = ["entity_id", "name", "symbols", "sector", "is_financial", "arena", "universe_mode", "max_source_date", "needs_verification", "is_synthetic"]
    result = table[fields].copy()
    result.attrs.update(table.attrs)
    return result
