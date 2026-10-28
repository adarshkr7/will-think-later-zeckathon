import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.eval.india_metrics import strict_lead_observations, wilson_interval


def test_wilson_hand_computed_and_empty_denominator():
    low, high = wilson_interval(5, 10, .95)
    assert low == pytest.approx(.23659309)
    assert high == pytest.approx(.76340691)
    assert pd.isna(wilson_interval(0, 0, .95)[0])


def test_strict_single_quarter_does_not_bridge_missing_snapshots():
    events = pd.read_csv(FIXTURES / "evaluation_cases.csv")
    predictions = pd.read_csv(FIXTURES / "evaluation_predictions.csv")
    rows = strict_lead_observations(predictions, events, 4).set_index("entity_id")
    assert rows.loc["FIX_A", "hit"] == 1
    assert rows.loc["FIX_A", "required_scoring_date"] == pd.Timestamp("2018-12-31", tz="UTC")
    assert rows.loc["FIX_B", "hit"] == 0
    assert rows.loc["FIX_B", "status"] == "no_snapshot_at_required_lead"
