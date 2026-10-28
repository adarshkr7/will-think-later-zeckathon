"""Rating observations remain unknown when no dated release is available."""

import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.manual import read_manual


def ratings_as_of(config: Config, t: str | pd.Timestamp) -> pd.DataFrame:
    return as_of(read_manual(config, "rating_actions"), t)
