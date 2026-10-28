import numpy as np
import pandas as pd

from conftest import FIXTURES
from prahari.features.chs import chs_score, relative_chs_features


def test_standardized_chs_exactly_cancels_unknown_common_market_total(config):
    source = pd.read_csv(FIXTURES / "chs_projection.csv")
    source["max_source_date"] = pd.to_datetime(source.max_source_date, utc=True)
    source.attrs["as_of"] = "2019-09-30T00:00:00+00:00"
    settings = config.section("feature_config")["chs"]
    relative = relative_chs_features(source, settings)
    for market_total in (1000, 10000):
        values = source.assign(relsize=np.log(source.market_cap/market_total))
        raw = pd.Series([chs_score(row, settings).value for row in values.to_dict(orient="records")])
        expected = (raw-raw.median())/(raw.quantile(.75)-raw.quantile(.25))
        assert np.allclose(relative.chs_standardized, expected, atol=1e-12)
    assert all(chs_score(row, settings).reason == "missing:relsize" for row in source.to_dict(orient="records"))
    rescaled = source.assign(market_cap=source.market_cap*1000)
    rescaled.attrs.update(source.attrs)
    scaled = relative_chs_features(rescaled, settings)
    assert np.allclose(relative.market_size_centered, scaled.market_size_centered, atol=1e-12)
    assert relative.is_synthetic.eq(1).all()
