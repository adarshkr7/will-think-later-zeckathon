import math

import numpy as np
import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.policy.cost import cost_curve, expected_cost, realized_cost
from prahari.policy.threshold import bayes_threshold
from prahari.policy.watchlist import build_watchlist


def test_registered_cap_for_small_and_large_universes(config):
    policy = config.section("policy_config")
    fixture = pd.read_csv(FIXTURES / "policy.csv")
    for size in (0, 1, 12, 19, 20, 42, 800):
        frame = fixture.iloc[np.arange(size) % len(fixture)].copy().reset_index(drop=True)
        frame["entity_id"] = [f"FIX_{index:04d}" for index in range(size)]
        result = build_watchlist(frame, policy)
        assert result.deep_review.sum() <= math.floor(policy["alert_frac"] * size)
        assert result.loc[result.pd_4q.isna() & result.hard_trigger.eq(0), "rank"].isna().all()
    assert bayes_threshold(policy["cost_fn"], policy["cost_fp"]) == pytest.approx(1 / 21)


def test_hard_trigger_tie_order_containment_and_budget(config):
    policy = config.section("policy_config")
    fixture = pd.read_csv(FIXTURES / "policy.csv")
    frame = fixture.iloc[np.arange(20) % len(fixture)].copy().reset_index(drop=True)
    frame["entity_id"] = [f"FIX_{index:02d}" for index in range(20)]
    result = build_watchlist(frame, policy)
    chosen = result.loc[result.deep_review.eq(1)]
    assert chosen.entity_id.tolist() == ["FIX_01"]
    assert chosen.tier.item() == "tier1"
    assert result.loc[result.entity_id.eq("FIX_00"), "tier"].item() == "containment"


def test_expected_realized_cost_and_shadow_price_hand_computed(config):
    policy = config.section("policy_config")
    assert expected_cost(np.array([.2, .01]), np.array([True, False]), policy) == pytest.approx(1.0)
    assert realized_cost(np.array([1, 0]), np.array([False, True]), policy) == policy["cost_fn"] + policy["cost_fp"]
    assert np.isnan(expected_cost(np.array([np.nan]), np.array([False]), policy))
    curve = cost_curve(np.array([.2, .01]), policy, 2, is_synthetic=1)
    assert curve.iloc[0].next_slot_benefit == pytest.approx(3.2)
    assert curve.is_synthetic.eq(1).all()
