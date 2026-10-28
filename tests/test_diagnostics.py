import numpy as np
import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.eval.drift import psi_from_counts, population_stability
from prahari.policy.hysteresis import hysteresis_watchlist
from prahari.policy.watchlist import build_watchlist
from prahari.eval.policy_scenarios import policy_scenarios


def test_psi_matches_hand_computed_example_and_handles_constant_reference(config):
    assert psi_from_counts(np.array([2., 2.]), np.array([1., 3.]), 0) == pytest.approx(.25*np.log(3))
    settings = {**config.section("diagnostics_config")["drift"], "minimum_observations": 2}
    assert population_stability(np.array([1., 1.]), np.array([2., 2.]), settings)["psi"] > 0
    assert np.isnan(population_stability(np.array([np.nan]), np.array([1.]), settings)["psi"])


def test_hysteresis_and_budget_scenarios_do_not_mutate_primary_or_break_cap(config):
    source = pd.read_csv(FIXTURES / "placebo_predictions.csv")
    scores = source.loc[source.scoring_date.eq("2018-12-31")].copy()
    scores["hard_trigger"] = 0
    original = scores.copy(deep=True)
    policy = {**config.section("policy_config"), "alert_frac": .5}
    primary = build_watchlist(scores, policy)
    experiment = hysteresis_watchlist(scores, {"FIX_B"}, policy, config.section("diagnostics_config")["hysteresis"])
    assert primary.loc[primary.deep_review.eq(1), "entity_id"].item() == "FIX_A"
    assert experiment.loc[experiment.deep_review.eq(1), "entity_id"].item() == "FIX_B"
    assert experiment.deep_review.sum() == primary.deep_review.sum() == 1
    labels = pd.Series([1, 0], index=scores.index)
    scenarios = policy_scenarios(scores, labels, policy, {"review_slots": [1], "false_negative_cost_ratios": [20]})
    assert scenarios.realized_cost.item() == 0
    assert scenarios.is_counterfactual_budget.eq(1).all()
    assert scenarios.is_synthetic.eq(1).all()
    pd.testing.assert_frame_equal(scores, original)
