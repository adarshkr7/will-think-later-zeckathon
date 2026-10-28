"""Quarterly pledge observations, accessed only at their publication dates."""

import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.manual import read_manual


def shareholding_as_of(config: Config, t: str | pd.Timestamp) -> pd.DataFrame:
    return as_of(read_manual(config, "shareholding"), t)


def share_counts_as_of(config: Config, t: str | pd.Timestamp) -> pd.DataFrame:
    """Share counts from dated shareholding disclosures, in individual shares.

    Separate rows prevent a missing share count from erasing otherwise sourced
    pledge observations. Annual financial share counts are not substituted for
    the required shareholding-filings source.
    """
    table = read_manual(config, "share_counts")
    table["field"] = "shares_outstanding"
    table["value"] = table.shares_outstanding
    return as_of(table, t)
