import pandas as pd
import pytest

from prahari.data.asof import as_of, impute_public_dates


def test_strict_publication_boundary_and_historical_periods(observations):
    result = as_of(observations, "2018-09-30")
    assert len(result) == 4
    assert (result.public_date < pd.Timestamp("2018-09-30", tz="UTC")).all()
    assert result.loc[(result.entity_id == "FIXTURE_A") & (result.field == "assets"), "value"].tolist() == [80, 100]


def test_restatement_available_only_after_publication(observations):
    result = as_of(observations, "2018-10-01")
    current = result.loc[(result.entity_id == "FIXTURE_A") & (result.field == "assets")
                         & (result.period_end == pd.Timestamp("2018-03-31", tz="UTC"))]
    assert current.value.item() == 120


def test_ambiguous_versions_fail(observations):
    with pytest.raises(ValueError, match="Ambiguous"):
        as_of(pd.concat([observations, observations.iloc[:1]]), "2019-01-01")


def test_unknown_date_fails(observations):
    observations.loc[0, "public_date"] = None
    with pytest.raises(ValueError, match="Unknown dates"):
        as_of(observations, "2018-09-30")


@pytest.mark.parametrize("kind", ["results_lag_days", "annual_report_lag_days"])
def test_conservative_imputation(observations, config, kind):
    observations.loc[0, "public_date"] = None
    result = impute_public_dates(observations, lag_days=config.base["dates"][kind])
    expected = pd.Timestamp("2018-03-31", tz="UTC") + pd.Timedelta(days=config.base["dates"][kind])
    assert result.public_date.iloc[0] == expected
    assert result.date_is_imputed.iloc[0] == 1


def test_unverified_rows_excluded(observations):
    observations.loc[0, "needs_verification"] = 1
    result = as_of(observations, "2018-09-30")
    assert len(result) == 3
