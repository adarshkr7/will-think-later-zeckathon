import pytest

from prahari.data.report_extract import amount_columns
from conftest import FIXTURES


def test_reviewed_column_positions_parentheses_and_dash_cells():
    text = (FIXTURES / "statement.txt").read_text()
    assert amount_columns(text, "Total Assets", 3) == [100, 80, None]
    assert amount_columns(text, "Total Equity", 3) == [40, 30, None]
    assert amount_columns(text, "Profit / (Loss) for the Year (V-VI)", 2) == [10, -2]


def test_ambiguous_or_changed_statement_rows_fail_loudly():
    with pytest.raises(ValueError, match="ambiguous"):
        amount_columns("Total Assets 100 80\nTotal Assets 90 70", "Total Assets", 2)
    with pytest.raises(ValueError, match="Unexpected"):
        amount_columns("Total Assets 100", "Total Assets", 3)
