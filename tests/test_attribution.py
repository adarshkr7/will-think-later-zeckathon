import numpy as np
import pytest
from scipy.special import expit, logit

from prahari.explain.attribution import calibrated_margin_allocation, marginal_pd_points, reconcile
from prahari.explain.templates import TEMPLATES, driver_text


class Calibrator:
    def predict(self, scores):
        return expit(2 * logit(np.clip(scores, .000001, .999999)) - .5)


def test_calibrated_allocation_exactly_reconciles_including_zero_net_margin():
    raw = np.array([[.3, -.1, -.7], [1, -1, -.4]])
    base, contributions = calibrated_margin_allocation(raw, Calibrator(), .1, .2, .000001, .0001)
    prior_offset = logit(.2) - logit(.1)
    expected = 2 * raw.sum(axis=1) - .5 + prior_offset
    assert np.allclose(base + contributions.sum(axis=1), expected)
    assert np.allclose(contributions[0], [.6, -.2])
    assert np.allclose(contributions[1], [2, -2])


def test_reconciliation_refuses_wrong_total_and_removal_effect_is_exact():
    reconcile(-2, {"a": 1, "b": -.2}, -1.2, .000001)
    with pytest.raises(AssertionError):
        reconcile(-2, {"a": 1}, -.8, .000001)
    points = marginal_pd_points(-1, {"a": .5})
    assert points["a"] == pytest.approx((expit(-1) - expit(-1.5)) * 100)


def test_template_coverage_and_unknown_values_are_deterministic():
    assert len(TEMPLATES) >= 25
    assert "unknown" in driver_text("roa", {"value": float("nan")})
    assert driver_text("roa", {"value": .1}) == driver_text("roa", {"value": .1})
    with pytest.raises(ValueError, match="No deterministic"):
        driver_text("invented_driver", {})
