import numpy as np
import pandas as pd

from conftest import FIXTURES
from prahari.models.stacker import group_oof_stacker


def test_ablation_predictions_exclude_outer_groups(config):
    fixture = pd.read_csv(FIXTURES / "benchmark.csv")
    # This fixture is synthetic and is never exported or used by primary fitting.
    X = fixture.select_dtypes("number").drop(columns=[name for name in ("target", "is_synthetic", "row_id") if name in fixture]).iloc[:24, :2].copy()
    groups = np.repeat(np.arange(6), 4)
    labels = np.tile([0, 0, 1, 1], 6)
    probabilities, audit = group_oof_stacker(X, labels, groups, [1] * X.shape[1], config.section("model_config")["ablation"], config.seed)
    assert np.isfinite(probabilities).all()
    assert all(row["held_group"] not in row["fit_groups"] and row["status"] == "out_of_fold" for row in audit)
