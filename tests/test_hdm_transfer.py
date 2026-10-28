from types import SimpleNamespace

import numpy as np
import pandas as pd

from conftest import FIXTURES
from prahari.models.hdm import india_design, predict_india


def model():
    prep = SimpleNamespace(rank=True, prune=False, references_={name: np.array([900., 1000., 1100.]) for name in ("roa", "tl_ta")},
                           medians_={"roa": 1000., "tl_ta": 1000.})
    learner = SimpleNamespace(predict_proba=lambda X: np.column_stack([np.full(len(X), .8), np.full(len(X), .2)]))
    return SimpleNamespace(columns=["roa", "tl_ta"], pipeline=SimpleNamespace(named_steps={"preprocess": prep, "model": learner}),
                           calibrator=SimpleNamespace(predict=lambda p: p))


def test_india_ecdf_is_local_not_polish_winsorized_or_twice_ranked():
    raw = pd.read_csv(FIXTURES / "hdm_transfer.csv")[["roa", "tl_ta"]]
    design = india_design(model(), raw, 2)
    assert np.allclose(design.roa, [.25, .75, .5])
    assert np.allclose(design.tl_ta, [.75, .25, .5])
    assert design.loc[2, "tl_ta__missing"] == 1
    probability, _ = predict_india(model(), raw, {"minimum_hdm_cross_section": 2, "minimum_hdm_observed": 2})
    assert np.allclose(probability[:2], [.2, .2])
    assert np.isnan(probability[2])
