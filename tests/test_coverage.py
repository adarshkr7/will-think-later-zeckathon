import pandas as pd
import pytest

from prahari.eval.coverage import coverage_parity


def test_fisher_exact_hand_computed_example(config):
    # Fisher's standard 2x2 example [[1,9],[11,3]], two-sided p=0.002759456.
    ids = [f"FIX_{i}" for i in range(24)]
    cohorts = pd.DataFrame({"entity_id": ids, "role": ["case"]*10 + ["peer"]*14, "is_synthetic": 1})
    features = pd.DataFrame({"entity_id": ids, "value": [None]+[1]*9+[None]*11+[1]*3, "is_synthetic": 1})
    settings = dict(config.section("india_config")["coverage"], collection_causes={"value": "collection_induced"})
    result = coverage_parity(features, cohorts, ["value"], settings)
    assert result.fisher_p.item() == pytest.approx(.002759456, abs=1e-9)
    assert result.arena_u_eligible.item() == 0
    assert result.is_synthetic.item() == 1


def test_empty_cohorts_never_pass_parity(config):
    cohorts = pd.DataFrame(columns=["entity_id", "role", "is_synthetic"])
    features = pd.DataFrame(columns=["entity_id", "value", "is_synthetic"])
    result = coverage_parity(features, cohorts, ["value"], config.section("india_config")["coverage"])
    assert result.reason.item() == "insufficient_cohorts"
    assert result.arena_u_eligible.item() == 0
    assert result.needs_verification.item() == 1
