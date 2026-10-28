from pathlib import Path

import pandas as pd
import pytest

from prahari.data.identity import alias_map, remap_references


@pytest.fixture
def aliases():
    return pd.read_csv(Path(__file__).parent / "fixtures" / "entity_aliases.csv")


def test_only_verified_unique_internal_identity_proof_can_migrate(aliases):
    assert alias_map(aliases) == {"CASE_01": "IN0000000000"}
    ambiguous = pd.concat([aliases, aliases.head(1)], ignore_index=True)
    with pytest.raises(ValueError, match="Ambiguous"):
        alias_map(ambiguous)
    aliases.loc[0, "entity_id"] = "GUESSED_TICKER"
    with pytest.raises(ValueError, match="sourced Indian ISIN"):
        alias_map(aliases)


def test_identity_resolution_preserves_values_provenance_and_publication(aliases):
    original = aliases.assign(matched_to=aliases.alias)
    updated = remap_references(original, alias_map(aliases))
    assert updated.matched_to.tolist() == ["IN0000000000", "CASE_02"]
    preserved = original.columns.difference(["entity_id", "matched_to"])
    pd.testing.assert_frame_equal(original[preserved], updated[preserved])
    pd.testing.assert_series_equal(original.entity_id, updated.entity_id)
