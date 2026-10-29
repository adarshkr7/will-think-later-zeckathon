import copy

import numpy as np
import pytest
import pandas as pd
from types import SimpleNamespace
from scipy.special import logit

from conftest import FIXTURES
from prahari.models.primary import primary_logit, soft_contributions
from prahari.models.scoring import score_snapshot


def test_zero_indian_label_formula_and_unknown_prior(config):
    settings = copy.deepcopy(config.section("model_config")["primary"])
    values = {"is_financial": 0, "chs_standardized": 1, "delayed_filing_4q": 0}
    result, _ = primary_logit(values, .2, .1, "4q", settings, "U")
    assert np.isnan(result.value)
    settings["priors"]["4q"], settings["prior_source"] = .1, "fixture://prior"
    result, contributions = primary_logit(values, .2, .1, "4q", settings, "U")
    assert result.value == pytest.approx(logit(.2) + 1)
    assert sum(contributions.values()) == pytest.approx(result.value)
    del values["delayed_filing_4q"]
    assert "missing" in primary_logit(values, .2, .1, "4q", settings, "U")[0].reason


def test_soft_upgrade_does_not_cancel_an_observed_flag(config):
    settings = config.section("model_config")["primary"]
    values = {"auditor_exit_8q": 1, "rating_watch_neg_or_inc": 0, "rating_notch_delta_4q": -3,
              "pledge_delta_4q": 21, "delayed_filing_4q": 0, "going_concern_flag": 0, "caro_default_flag": 0}
    contributions = soft_contributions(values, settings, "P")
    assert contributions["rating_notch_delta_4q"] == 0
    assert contributions["auditor_exit_8q"] == settings["soft_weights"]["auditor_exit_8q"]
    assert contributions["pledge_jump"] == settings["soft_weights"]["pledge_jump"]


def test_mixed_financial_and_missing_rows_preserve_unavailable_hdm(config, monkeypatch):
    frame = pd.read_csv(FIXTURES / "primary_mixed.csv")
    frame.attrs["as_of"] = "2018-09-30T00:00:00+00:00"
    settings = copy.deepcopy(config.section("model_config"))
    settings["primary"].update(priors={"4q": .1, "8q": .1}, prior_source="fixture://prior", nbfc_logit_scale=1)
    model = SimpleNamespace(columns=["roa"], training_prior=.2)
    monkeypatch.setattr("prahari.models.scoring.predict_india", lambda *args:
                        (frame.hdm_probability.to_numpy(), pd.DataFrame(index=frame.index)))
    scored, _ = score_snapshot(frame, {"4q": model, "8q": model}, settings, "U")
    assert scored.loc[0, "pd_4q"] == pytest.approx(.1)
    assert np.isfinite(scored.loc[1, "pd_4q"])
    assert np.isnan(scored.loc[2, "pd_4q"])
    assert scored.loc[0, "hdm_logit_4q"] == pytest.approx(logit(.1))
    assert scored.loc[[1, 2], "hdm_logit_4q"].isna().all()
    assert scored.is_synthetic.eq(1).all()
