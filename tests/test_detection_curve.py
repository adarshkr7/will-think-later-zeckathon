import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.eval.detection_curve import is_sub_ig, rating_lead_comparison
from prahari.data.firewall import write_real_table


def test_rating_lead_uses_publication_date_and_keeps_unpaired_cases(config, tmp_path):
    events = pd.read_csv(FIXTURES / "evaluation_cases.csv")
    predictions = pd.read_csv(FIXTURES / "evaluation_predictions.csv")
    ratings = pd.read_csv(FIXTURES / "detection_ratings.csv")
    settings, scales = config.section("model_config")["evaluation"], config.section("feature_config")["soft"]
    cases, summary = rating_lead_comparison(predictions, events, ratings, settings, scales, "P")
    indexed = cases.set_index("entity_id")
    assert indexed.loc["FIX_A", "first_sourced_sub_ig_public_date"] == pd.Timestamp("2019-06-03", tz="UTC")
    assert indexed.loc["FIX_A", "lead_calendar_quarters"] == 2
    assert indexed.loc["FIX_A", "lead_days"] == 154
    assert pd.isna(indexed.loc["FIX_B", "lead_calendar_quarters"])
    assert summary.paired_observed_cases.item() == 1
    assert summary.cases.item() == 2
    assert summary.needs_verification.item() == 1
    earlier_only = ratings.loc[ratings.public_date.lt("2020-01-15")]
    unchanged, _ = rating_lead_comparison(predictions, events, earlier_only, settings, scales, "P")
    pd.testing.assert_frame_equal(cases, unchanged)
    assert is_sub_ig("CARE BBB-", scales, settings) is False
    assert is_sub_ig("CARE A4+", scales, settings) is True
    assert is_sub_ig("withdrawn", scales, settings) is None
    with pytest.raises(ValueError, match="Synthetic"):
        write_real_table(summary, tmp_path / "forbidden.csv")
