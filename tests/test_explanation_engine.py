import copy
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy.special import expit, logit

from conftest import FIXTURES
from prahari.explain.engine import explain_snapshot
from prahari.features.chs import chs_score
from prahari.models.primary import primary_logit


def test_engine_aligns_ranked_rows_and_reconciles_full_calibrated_score(config, monkeypatch):
    features = pd.read_csv(FIXTURES / "explanation.csv")
    features.attrs["as_of"] = "2019-12-31T00:00:00+00:00"
    features["chs_standardized"] = [(chs_score(row, config.section("feature_config")["chs"]).value-row["chs_center"])/row["chs_scale"] for row in features.to_dict(orient="records")]
    settings = copy.deepcopy(config.section("model_config"))
    settings["primary"]["priors"]["4q"] = .2
    settings["primary"]["prior_source"] = "fixture://prior"
    original = config.section
    monkeypatch.setattr(config, "section", lambda key: settings if key == "model_config" else original(key))
    design = features[["roa", "tl_ta"]].copy()
    design["roa__missing"], design["tl_ta__missing"] = 0., 0.
    def contributions(X, pred_contrib):
        assert pred_contrib
        return np.column_stack([X.to_numpy()*np.array([.2, -.1, 0, 0]), np.full(len(X), -1)])
    calibrator = SimpleNamespace(predict=lambda p: expit(2*logit(p)-.5))
    learner = SimpleNamespace(predict=contributions)
    model = SimpleNamespace(pipeline=SimpleNamespace(named_steps={"model": learner}), calibrator=calibrator, training_prior=.1)
    probabilities = calibrator.predict(expit(contributions(design, True).sum(axis=1)))
    scores = []
    for row, probability in zip(features.to_dict(orient="records"), probabilities, strict=True):
        margin, _ = primary_logit(row, probability, .1, "4q", settings["primary"], "U")
        assert not margin.reason
        scores.append({"entity_id": row["entity_id"], "pd_4q": expit(margin.value), "logit_4q": margin.value,
                       "deep_review": 0, "arena": "U"})
    captured = []
    monkeypatch.setattr("prahari.explain.engine.write_real_table", lambda frame, path: captured.append(frame.copy()))
    result = explain_snapshot(config, features, pd.DataFrame(scores).iloc[::-1].reset_index(drop=True),
                              {"4q": model}, {"4q": design}, None)
    assert len(captured) == 1 and result.is_synthetic.eq(1).all()
    for entity, rows in result.groupby("entity_id"):
        assert np.isclose(rows.intercept.iloc[0] + rows.logit_contribution.sum(), rows.final_logit.iloc[0], atol=1e-6)
        assert np.isclose(rows.final_logit.iloc[0], next(row["logit_4q"] for row in scores if row["entity_id"] == entity))
