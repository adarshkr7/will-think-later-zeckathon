import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.features.common import financial_snapshot
from prahari.features.forensic import altman_classic, altman_em, beneish, forensic_features, hillegeist, piotroski
from prahari.features.chs import chs_score, weighted_average


@pytest.fixture
def row():
    return pd.read_csv(FIXTURES / "forensic.csv").iloc[0].to_dict()


def test_altman_and_hillegeist_hand_computed(config, row):
    settings = config.section("feature_config")
    assert altman_classic(row, settings["altman"]["classic"]).value == pytest.approx(2.91)
    assert altman_em(row, settings["altman"]["em"]).value == pytest.approx(6.26)
    assert hillegeist(row, settings["hillegeist"]).value == pytest.approx(-4.742)


def test_beneish_and_piotroski_hand_computed(config, row):
    settings = config.section("feature_config")
    # Indices: 2, .75, 1, 1, 7/9, 1, -.02, 8/11; eight F signals pass.
    assert beneish(row, settings["beneish"]).value == pytest.approx(-1.7219537374)
    assert piotroski(row).value == 8
    del row["cfo"]
    assert "missing:cfo" in beneish(row, settings["beneish"]).reason


def test_zero_division_and_financial_exemption(config, row):
    settings = config.section("feature_config")
    row["total_assets"] = 0
    assert "invalid" in altman_em(row, settings["altman"]["em"]).reason
    row["is_financial"] = 1
    table = pd.DataFrame([row])
    table.attrs["as_of"] = "2019-10-01T00:00:00+00:00"
    result = forensic_features(table, settings)
    assert pd.isna(result.z_em.item())
    assert result.z_em__reason.item() == "not_applicable_financial_firm"


def test_chs_published_linear_score_and_quarter_weights(config):
    values = {"nimtaavg": .01, "tlmta": .5, "exretavg": 0, "sigma": .2,
              "relsize": -5, "cashmta": .1, "mb": 2, "price": 1}
    assert chs_score(values, config.section("feature_config")["chs"]).value == pytest.approx(-8.2666)
    assert weighted_average([1, 2, 3, 4], .5).value == pytest.approx(26 / 15)
    assert weighted_average([1, float("nan")], .5).reason == "incomplete_weighted_history"


def test_financial_year_lags_do_not_bridge_missing_years(config):
    from prahari.data.asof import as_of
    from prahari.data.financials import financial_table
    table = as_of(financial_table(config), "2018-09-30")
    snapshot = financial_snapshot(table, "standalone")
    if not snapshot.empty:
        assert pd.to_datetime(snapshot.max_source_date, utc=True).lt(pd.Timestamp("2018-09-30", tz="UTC")).all()
