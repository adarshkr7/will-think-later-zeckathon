import numpy as np
from sklearn.base import clone

from prahari.models.benchmark import FittedBenchmark, make_pipeline
from prahari.models.calibrate import ProbabilityCalibrator


def test_transfer_has_separate_target_training_reference(benchmark_fixture, config):
    X = benchmark_fixture[["a", "b", "c"]]
    y = benchmark_fixture.target.to_numpy()
    settings = config.section("benchmark_config")
    pipeline = make_pipeline(settings, config.seed, "none", monotone=[-1, 1, -1])
    pipeline.set_params(model__n_estimators=3, model__min_child_samples=2)
    pipeline.fit(X.iloc[:20], y[:20])
    calibrator = ProbabilityCalibrator(1, config.seed).fit(np.linspace(0, 1, len(y)), y)
    model = FittedBenchmark(pipeline, calibrator, list(X), y[:20].mean(), {}, tuple(X.index[:20]), "harmonized", "fixture")
    target = X.iloc[20:30] / 1000
    model.transfer_preprocessor = clone(pipeline.named_steps["preprocess"]).fit(target)
    prediction = model.predict_transfer(X.iloc[30:] / 1000)
    assert np.isfinite(prediction).all()
    assert set(model.transfer_preprocessor.fit_indices_).isdisjoint(X.index[30:])
    assert model.transfer_preprocessor.medians_.a < pipeline.named_steps["preprocess"].medians_.a
