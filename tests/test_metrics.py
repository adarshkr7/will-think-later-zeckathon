import numpy as np
import pytest

from prahari.eval.metrics import benchmark_metrics, wilson_interval
from prahari.models.prior_shift import prior_shift
from prahari.policy.threshold import bayes_threshold


def test_prior_shift_hand_calculation():
    # Prior odds fall by 9x: posterior odds 1 become 1/9, posterior = 1/10.
    assert prior_shift(0.5, pi_old=0.5, pi_new=0.1) == pytest.approx(0.1)
    assert prior_shift(0.8, pi_old=0.5, pi_new=0.1) == pytest.approx(4/13)
    np.testing.assert_allclose(prior_shift(np.array([0, 1]), 0.5, 0.1), [0, 1])


@pytest.mark.parametrize("old,new,p", [(0, .1, .2), (.1, 1, .2), (.1, .2, -1), (.1, .2, float("nan"))])
def test_prior_shift_invalid_input(old, new, p):
    with pytest.raises(ValueError):
        prior_shift(p, old, new)


def test_threshold_from_configuration(config):
    policy = config.section("policy_config")
    assert bayes_threshold(policy["cost_fn"], policy["cost_fp"]) == pytest.approx(1/21)


def test_metrics_on_fixture_without_persisting_synthetic_data(benchmark_fixture, config):
    settings = dict(config.section("benchmark_config")["metrics"], bootstrap_resamples=10)
    p = benchmark_fixture.target.to_numpy() * .8 + .1
    row = benchmark_metrics(benchmark_fixture.target.to_numpy(), p, settings, config.section("policy_config"), config.seed)
    assert row["pr_auc"] == 1
    assert row["brier"] == pytest.approx(.01)
    assert row["base_rate"] == .5
    assert row["recall_at_cap"] == .1


def test_wilson_hand_calculation():
    # With zero successes lower bound = 0, upper = z^2/(n+z^2).
    low, high = wilson_interval(0, 10, .95)
    assert low == pytest.approx(0, abs=1e-12)
    assert high == pytest.approx(.2775328, abs=1e-6)
    assert np.isnan(wilson_interval(0, 0, .95)[0])
