import numpy as np
import pandas as pd

from conftest import FIXTURES
from prahari.eval.operating_metrics import verified_window_labels
from prahari.eval.placebo import within_firm_placebo


def test_absent_background_event_is_not_a_verified_negative(config):
    cases = pd.read_csv(FIXTURES / "evaluation_cases.csv")
    predictions = pd.read_csv(FIXTURES / "hdm_transfer.csv")
    predictions["scoring_date"] = pd.read_csv(FIXTURES / "evaluation_predictions.csv").scoring_date.iloc[0]
    survival = pd.DataFrame(columns=config.section("manual_config")["tables"]["peer_survival"]["columns"])
    labels = verified_window_labels(predictions, cases, survival, 4)
    assert labels.iloc[0] == 0 and labels.iloc[1] == 0
    assert np.isnan(labels.iloc[2])


def test_placebo_is_seeded_keeps_original_dates_and_propagates_taint(config):
    predictions = pd.read_csv(FIXTURES / "placebo_predictions.csv")
    cases = pd.read_csv(FIXTURES / "evaluation_cases.csv")
    original = cases.copy(deep=True)
    first = within_firm_placebo(predictions, cases, config.section("model_config")["evaluation"], config.seed, "P")
    second = within_firm_placebo(predictions, cases, config.section("model_config")["evaluation"], config.seed, "P")
    pd.testing.assert_frame_equal(first, second)
    pd.testing.assert_frame_equal(cases, original)
    assert first.status.eq("completed").all()
    assert first.observed_recall.eq(.5).all()
    assert first.is_synthetic.eq(1).all()
    predictions.loc[0, "pd_4q"] = np.nan
    blocked = within_firm_placebo(predictions, cases, config.section("model_config")["evaluation"], config.seed, "P")
    assert blocked.loc[blocked.lead_quarters.eq(4), "null_mean"].isna().all()
