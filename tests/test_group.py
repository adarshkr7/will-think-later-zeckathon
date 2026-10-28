import pandas as pd

from conftest import FIXTURES
from prahari.data.asof import as_of
from prahari.features.group import group_features


def test_group_stress_uses_siblings_and_sourced_complete_singletons():
    states = pd.read_csv(FIXTURES / "group_states.csv")
    states["max_source_date"] = pd.to_datetime(states.max_source_date, utc=True)
    states.attrs["as_of"] = "2019-09-30T00:00:00+00:00"
    groups = as_of(pd.read_csv(FIXTURES / "group_membership.csv"), "2019-09-30")
    result = group_features(states, groups, .9).set_index("entity_id")
    assert result.loc["FIX_A", "group_stress"] == 1
    assert result.loc["FIX_C", "group_stress"] == 0
    assert result.is_synthetic.eq(1).all()
    groups.loc[groups.entity_id.eq("FIX_C"), "membership_complete"] = 0
    result = group_features(states, groups, .9).set_index("entity_id")
    assert pd.isna(result.loc["FIX_C", "group_stress"])
