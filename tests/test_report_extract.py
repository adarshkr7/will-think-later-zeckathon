import json

import pytest

from prahari.data.report_extract import (amount_columns, join_spaced_thousands,
                                       require_denomination, reviewed_table_text, reviewed_values)
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


def test_interleaved_statement_subtotals_preserve_year_positions():
    text = (FIXTURES / "statement_subtotals.txt").read_text()
    rule = {"label": "Reserves and surplus", "columns": 4, "positions": [1, 3]}
    assert reviewed_values(text, rule, 2, 2) == [40, 25]
    assert reviewed_values(text, {"label": "Total", "occurrence": 1, "expected_matches": 2}, 2, 2) == [100, 80]
    with pytest.raises(ValueError, match="ambiguous"):
        reviewed_values(text, "Total", 2, 2)
    with pytest.raises(ValueError, match="column positions"):
        reviewed_values(text, dict(rule, positions=[1, 1]), 2, 2)


def test_reviewed_amount_only_subtotal_offset_and_ligatures():
    text = (FIXTURES / "statement_offset.txt").read_text(encoding="utf-8")
    assert reviewed_values(text, {"label": "Reserves and surplus", "line_offset": 1}, 2, 2) == [40, 25]
    assert reviewed_values(text, "Net Profit for the year", 2, 1) == [10]
    with pytest.raises(ValueError, match="amount-only"):
        reviewed_values(text, {"label": "Reserves and surplus", "line_offset": 2}, 2, 2)


def test_reviewed_sum_uses_only_complete_printed_components():
    text = (FIXTURES / "statement_sum.txt").read_text()
    rule = {"sum": ["Total non-current liabilities", "Total current liabilities"]}
    assert reviewed_values(text, rule, 3, 3) == [80.75, 60, None]
    assert amount_columns(text, "Spaced total", 2) == [10757247, 7154635]
    with pytest.raises(ValueError, match="twice"):
        reviewed_values(text, {"sum": ["Total current liabilities", "Total current liabilities"]}, 3, 3)
    with pytest.raises(ValueError, match="ambiguous"):
        reviewed_values(text, {"sum": ["Absent component", "Total current liabilities"]}, 3, 3)


def test_reviewed_liability_identity_preserves_missing_operands():
    text = (FIXTURES / "statement_sum.txt").read_text()
    rule = {"difference": ["Total assets", {"sum": ["Equity share capital", "Other equity"]}]}
    assert reviewed_values(text, rule, 3, 3) == [70.75, 60, None]
    with pytest.raises(ValueError, match="exactly two"):
        reviewed_values(text, {"difference": ["Total assets"]}, 3, 3)


def test_opt_in_layout_grouping_preserves_distinct_columns_and_dash():
    text = (FIXTURES / "statement_sum.txt").read_text()
    normalized = join_spaced_thousands(text)
    assert amount_columns(normalized, "Layout grouped values", 3) == [13915, 14168, None]


def test_literal_currency_guard_never_accepts_absent_or_empty_marker():
    text = json.loads((FIXTURES / "statement_pages.json").read_text())["pages"][0]
    require_denomination(text, {"unit": "INR", "unit_marker_literal": "`"}, {}, {})
    for marker in ["", " ", "Rs"]:
        with pytest.raises(ValueError, match="denomination"):
            require_denomination(text, {"unit": "INR", "unit_marker_literal": marker}, {}, {})
    with pytest.raises(ValueError, match="denomination"):
        require_denomination(text, {"unit": "INR"}, {}, {})


def test_continuation_pages_are_explicit_and_keep_source_order():
    fixture = json.loads((FIXTURES / "statement_pages.json").read_text())
    class Page:
        def __init__(self, value):
            self.value = value

        def extract_text(self, **kwargs):
            return self.value

    class Reader:
        pages = [Page(value) for value in fixture["pages"]]

    assert reviewed_table_text(Reader(), {"page": 1, "additional_pages": [2]}) == ("\n".join(fixture["pages"][:2]), [1, 2])
    for pages in [[1], [0], [4]]:
        with pytest.raises(ValueError, match="pages"):
            reviewed_table_text(Reader(), {"page": 1, "additional_pages": pages})
