import pandas as pd
import pytest

from prahari.data.quality import validate_manual, validate_table


def test_manual_headers_validate(config):
    summary = validate_manual(config)
    assert set(summary.table) == set(config.section("manual_config")["tables"])
    assert (summary.rows >= summary.verified).all()


def test_empty_panel_does_not_pass_data_acceptance(config):
    settings = config.section("manual_config")
    for name, minimum in (("events", "minimum_events"), ("peers", "minimum_peers")):
        empty = pd.DataFrame(columns=settings["tables"][name]["columns"])
        result = validate_table(empty, name, settings)
        assert result["verified"] < settings["validation"][minimum]


def test_synthetic_manual_record_is_rejected(config):
    settings = config.section("manual_config")
    columns = settings["tables"]["events"]["columns"]
    row = {column: None for column in columns}
    row.update(entity_id="FIXTURE_ONLY", is_synthetic=1, needs_verification=1, date_is_imputed=0)
    with pytest.raises(ValueError, match="synthetic"):
        validate_table(pd.DataFrame([row]), "events", settings)
