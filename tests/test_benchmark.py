import copy

import numpy as np
import pytest
from sklearn.base import clone

from prahari.models.benchmark import make_pipeline, nested_development
from prahari.models.calibrate import ProbabilityCalibrator
from prahari.models.preprocess import FoldPreprocessor


@pytest.mark.parametrize("variant", ["none", "class_weight", "logistic"])
def test_real_pipeline_clone_and_fit(benchmark_fixture, config, variant):
    settings = copy.deepcopy(config.section("benchmark_config"))
    settings["models"]["lightgbm"].update(n_estimators=3, min_child_samples=2)
    pipeline = clone(make_pipeline(settings, config.seed, variant))
    X = benchmark_fixture[["a", "b", "c"]]
    pipeline.fit(X.iloc[:30], benchmark_fixture.target.iloc[:30])
    p = pipeline.predict_proba(X.iloc[30:])[:, 1]
    assert np.isfinite(p).all()
    assert set(pipeline.named_steps["preprocess"].fit_indices_).isdisjoint(X.index[30:])
    if variant != "logistic":
        assert pipeline.named_steps["model"].get_params()["deterministic"] is True


def test_nested_selection_and_calibration_exclude_outer_fold(benchmark_fixture, config, monkeypatch):
    settings = copy.deepcopy(config.section("benchmark_config"))
    settings["cv"].update(outer_folds=2, inner_folds=2, calibration_folds=2)
    settings["models"]["grid"] = {"num_leaves": [3], "n_estimators": [3], "min_child_samples": [2]}
    settings["cv"]["n_jobs"] = 1  # Keep the fit spy in this process.
    X = benchmark_fixture[["a", "b", "c"]]
    observed_fits = []
    original = FoldPreprocessor.fit
    def record_fit(transformer, frame, y=None):
        observed_fits.append(set(frame.index))
        return original(transformer, frame, y)
    monkeypatch.setattr(FoldPreprocessor, "fit", record_fit)
    # Treat the fixture's last rows as reserved: no transform, tuning fold or
    # calibration fold may ever fit them. No production hold-out is opened.
    train = X.iloc[:32]
    result = nested_development(train, benchmark_fixture.target.to_numpy()[:32], settings, config.seed, "class_weight", source="fixture")
    assert np.isfinite(result.probabilities).all()
    assert len(result.folds) == 2
    assert all(fold["fit_validation_overlap"] == 0 for fold in result.folds)
    assert set(result.model.fit_indices) == set(train.index)
    assert observed_fits and all(fit <= set(train.index) for fit in observed_fits)
    assert all(fit.isdisjoint(X.index[32:]) for fit in observed_fits)


@pytest.mark.parametrize("minimum,kind", [(50, "platt"), (1, "isotonic")])
def test_calibration_branch(benchmark_fixture, config, minimum, kind):
    y = benchmark_fixture.target.to_numpy()
    scores = benchmark_fixture.a.to_numpy() / benchmark_fixture.a.max()
    model = ProbabilityCalibrator(minimum, config.seed).fit(scores, y)
    assert model.kind_ == kind
    assert np.isfinite(model.predict(scores)).all()


def test_smote_not_a_production_variant(config):
    with pytest.raises(ValueError, match="Unregistered"):
        make_pipeline(config.section("benchmark_config"), config.seed, "smote")
