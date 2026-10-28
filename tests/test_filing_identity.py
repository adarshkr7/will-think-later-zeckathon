import json

import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.data.asof import as_of
from prahari.data.filing_identity import filing_identity
from prahari.data.firewall import write_real_table


def test_identity_uses_exact_isin_latest_timestamp_and_preserves_taint(tmp_path):
    row = json.loads((FIXTURES / "filing_identity.json").read_text())
    mapping = filing_identity(row, {"FIX_IDENTITY"}, "fixture://filings", "Asia/Kolkata")
    assert mapping["exchange_code"] == "FIX_OLD_SYMBOL"
    assert mapping["public_date"] == "2011-06-29T06:31:10+00:00"
    assert mapping["date_is_imputed"] == 0
    table = pd.DataFrame([mapping])
    assert as_of(table, mapping["public_date"]).empty
    assert len(as_of(table, "2011-06-29T06:31:11Z")) == 1
    with pytest.raises(ValueError, match="Synthetic"):
        write_real_table(table, tmp_path / "forbidden.csv")
    assert filing_identity(row, {"FIX_OTHER"}, "fixture://filings", "Asia/Kolkata") is None
    for key in ("broadCastDate", "filingDate", "exchdisstime"):
        row[key] = None
    assert filing_identity(row, {"FIX_IDENTITY"}, "fixture://filings", "Asia/Kolkata") is None
