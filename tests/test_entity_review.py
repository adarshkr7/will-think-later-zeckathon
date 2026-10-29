import pytest
import pandas as pd

from conftest import FIXTURES
from prahari.data.entity_review import merge_reviewed_entities, require_reviewed_text


def test_classification_review_checks_literal_source_proof():
    require_reviewed_text("An infra-structure financing NBFC.", ["infrastructure financing", "NBFC"])
    with pytest.raises(ValueError, match="changed or is missing"):
        require_reviewed_text("A textile manufacturer.", ["housing finance"])
    with pytest.raises(ValueError, match="changed or is missing"):
        require_reviewed_text("Anything", [])


def test_recovered_identity_appends_earlier_classification_without_replacing_human_sources():
    rows = pd.read_csv(FIXTURES / "entity_merge.csv")
    merged = merge_reviewed_entities(rows.iloc[:1], rows.iloc[1:])
    assert len(merged) == 2
    assert merged.iloc[0].source_url == "fixture://old_identity;fixture://alternate_identity"
    changed = rows.iloc[1:2].copy()
    changed["sector"] = "fixture_different_sector"
    with pytest.raises(ValueError, match="conflicts"):
        merge_reviewed_entities(rows.iloc[:1], changed)
