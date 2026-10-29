import json

import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.data.asof import as_of
from prahari.data.filing_identity import filing_identity
from prahari.data.firewall import write_real_table


def test_identity_uses_exact_isin_latest_timestamp_and_preserves_taint(config, tmp_path):
    row = json.loads((FIXTURES / "filing_identity.json").read_text())
    settings = config.section("financial_index_config")
    mapping = filing_identity(row, {"FIX_IDENTITY"}, "fixture://filings", settings)
    assert mapping["exchange_code"] == "FIX_OLD_SYMBOL"
    assert mapping["public_date"] == "2011-06-29T06:31:10+00:00"
    assert mapping["date_is_imputed"] == 0
    assert mapping["needs_verification"] == 1
    table = pd.DataFrame([mapping])
    assert as_of(table, mapping["public_date"]).empty
    assert as_of(table, "2011-06-29T06:31:11Z").empty
    with pytest.raises(ValueError, match="Synthetic"):
        write_real_table(table, tmp_path / "forbidden.csv")
    assert filing_identity(row, {"FIX_OTHER"}, "fixture://filings", settings) is None
    assert filing_identity({**row, "symbol": "FIX_CURRENT_SYMBOL"}, {"FIX_IDENTITY"}, "fixture://filings", settings) is None
    for key in ("broadCastDate", "filingDate", "exchdisstime"):
        row[key] = None
    assert filing_identity(row, {"FIX_IDENTITY"}, "fixture://filings", settings) is None
