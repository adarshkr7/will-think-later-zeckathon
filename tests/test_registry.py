from pathlib import Path

import pandas as pd
import pytest

from prahari.data.registry import parse_announcements

FIXTURE = Path(__file__).parent / "fixtures" / "registry.html"


def test_registry_discovers_debtors_without_assigning_labels_or_importing_other_parties(config):
    settings = config.section("registry_config")
    records, last = parse_announcements(FIXTURE.read_text(), settings["url"], settings,
                                       page=1, is_synthetic=1)
    assert last == 3
    assert [row["corporate_debtor_name"] for row in records] == ["Fixture Debtor Ltd", "Fixture Solvent Ltd"]
    assert records[0]["period_end"] == pd.Timestamp("2019-06-15", tz="UTC")
    assert pd.isna(records[1]["period_end"])
    assert records[0]["source_url"] == "https://ibbi.gov.in/uploads/fixture.pdf"
    assert records[1]["source_url"] == settings["url"]
    assert all(row["entity_id"] is None and row["needs_verification"] == 1
               and row["is_synthetic"] == 1 for row in records)
    assert "fixture-only-do-not-import" not in str(records)
    assert "Fixture Creditor" not in str(records)


@pytest.mark.parametrize("old,new,message", [
    ("?page=3", "?page=0", "pagination"),
    ("?page=3", "?page=3&page=4", "pagination"),
    ("<td>Fixture Debtor Ltd</td>", "", "columns"),
    ("<td>Fixture Debtor Ltd</td>", "<td></td>", "debtor"),
    ("Name of Corporate Debtor</th>", "Different header</th>", "Missing/empty"),
])
def test_registry_fails_on_unreviewed_source_structure(config, old, new, message):
    settings = config.section("registry_config")
    with pytest.raises(ValueError, match=message):
        parse_announcements(FIXTURE.read_text().replace(old, new), settings["url"], settings,
                            page=1, is_synthetic=1)
