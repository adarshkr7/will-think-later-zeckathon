import pandas as pd
import pytest

from prahari.data.asof import as_of
from prahari.features.panel import select_peers
from conftest import FIXTURES


def test_peer_matching_distance_sector_and_stressed_quota(config):
    snapshot = as_of(pd.read_csv(FIXTURES / "peer_snapshot.csv"), "2017-01-01")
    eligible = set(snapshot.entity_id) - {"FIX_CASE"}
    selected = select_peers(snapshot, "FIX_CASE", eligible, config.section("india_config")["panel"])
    assert list(selected.entity_id) == ["FIX_B", "FIX_A", "FIX_E"]
    assert selected.is_stressed_survivor.sum() == 1
    assert selected.is_synthetic.eq(1).all()
    assert selected.matched_to.eq("FIX_CASE").all()


def test_no_eligibility_evidence_no_peer_selection(config):
    snapshot = as_of(pd.read_csv(FIXTURES / "peer_snapshot.csv"), "2017-01-01")
    with pytest.raises(ValueError, match="Insufficient verified"):
        select_peers(snapshot, "FIX_CASE", set(), config.section("india_config")["panel"])


def test_peer_selection_rejects_raw_or_future_data(config):
    table = pd.read_csv(FIXTURES / "peer_snapshot.csv")
    with pytest.raises(ValueError, match="as_of snapshot"):
        select_peers(table, "FIX_CASE", set(table.entity_id), config.section("india_config")["panel"])
    snapshot = as_of(table, "2017-01-01")
    snapshot.loc[0, "max_source_date"] = pd.Timestamp("2018-01-01", tz="UTC")
    with pytest.raises(ValueError, match="future sources"):
        select_peers(snapshot, "FIX_CASE", set(table.entity_id), config.section("india_config")["panel"])


def test_unknown_leverage_is_not_classified_as_an_unstressed_peer(config):
    table = pd.read_csv(FIXTURES / "peer_snapshot.csv")
    table.loc[table.entity_id.ne("FIX_CASE"), "total_liabilities"] = float("nan")
    snapshot = as_of(table, "2017-01-01")
    with pytest.raises(ValueError, match="Insufficient verified"):
        select_peers(snapshot, "FIX_CASE", set(table.entity_id), config.section("india_config")["panel"])
