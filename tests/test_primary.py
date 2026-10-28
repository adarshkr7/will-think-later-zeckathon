import copy

import numpy as np
import pytest
from scipy.special import logit

from prahari.models.primary import primary_logit, soft_contributions


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
