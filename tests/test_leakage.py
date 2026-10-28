import pandas as pd
import pytest
from sklearn.base import clone

from prahari.data.asof import as_of
from prahari.models.preprocess import FoldPreprocessor


def test_deleting_all_future_rows_does_not_change_snapshot(observations):
    t = "2018-09-30"
    snapshot = as_of(observations, t)
    before = observations.loc[pd.to_datetime(observations.public_date) < pd.Timestamp(t)]
    pd.testing.assert_frame_equal(snapshot, as_of(before, t))
    assert (snapshot.max_source_date < pd.Timestamp(t, tz="UTC")).all()


def test_extreme_validation_values_never_change_fit(benchmark_fixture, config):
    X = benchmark_fixture[["a", "b", "c"]]
    settings = config.section("benchmark_config")["preprocessing"]
    prep = FoldPreprocessor(**{k: settings[k] for k in ("lower_quantile", "upper_quantile", "correlation_threshold")})
    train, valid = X.iloc[:30], X.iloc[30:].copy()
    fitted = prep.fit(train)
    medians = fitted.medians_.copy()
    upper = fitted.upper_.copy()
    valid.loc[:, "a"] = 1e12
    fitted.transform(valid)
    assert set(fitted.fit_indices_).isdisjoint(valid.index)
    pd.testing.assert_series_equal(fitted.medians_, medians)
    pd.testing.assert_series_equal(fitted.upper_, upper)
    assert clone(prep).get_params() == prep.get_params()


def test_rank_reference_is_fitted_on_training_only(benchmark_fixture, config):
    X = benchmark_fixture[["a", "b"]]
    settings = config.section("benchmark_config")["preprocessing"]
    prep = FoldPreprocessor(settings["lower_quantile"], settings["upper_quantile"],
                            settings["correlation_threshold"], rank=True, prune=False).fit(X.iloc[:20])
    reference = prep.references_["a"].copy()
    ranked = prep.transform(X.iloc[20:])
    assert (ranked.a <= 1).all()
    assert (prep.references_["a"] == reference).all()
    assert set(prep.fit_indices_).isdisjoint(X.index[20:])


def test_all_missing_is_nan_with_explicit_reason(benchmark_fixture, config):
    X = benchmark_fixture[["a"]].astype(float)
    X.loc[:, "a"] = float("nan")
    prep = FoldPreprocessor(0, 1, 1).fit(X)
    result = prep.transform(X)
    assert result.a.isna().all()
    assert prep.empty_columns_ == ("a",)
    assert result.a__missing.eq(1).all()
