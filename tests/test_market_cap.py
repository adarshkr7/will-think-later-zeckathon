import pandas as pd
import pytest

from prahari.data.asof import as_of
from prahari.data.market_cap import market_cap
from conftest import FIXTURES


def inputs():
    fixture = pd.read_csv(FIXTURES / "asof.csv").iloc[:1].copy()
    shares = fixture.assign(field="shares_outstanding", value=100)
    prices = fixture.assign(close=10, series="EQ", exchange="nse", symbol="FIX_A")
    return as_of(prices, "2018-09-30"), as_of(shares, "2018-09-30")


def test_market_cap_hand_computed_and_source_dates(config):
    prices, shares = inputs()
    result = market_cap(prices, shares, config.section("india_config")["market"])
    assert result.market_cap.item() == 1000  # 10 currency/share × 100 shares.
    assert result.max_source_date.item() == pd.Timestamp("2018-06-01", tz="UTC")
    assert result.is_synthetic.eq(1).all()


def test_missing_shares_produce_nan_with_reason(config):
    prices, shares = inputs()
    shares = shares.iloc[:0]
    result = market_cap(prices, shares, config.section("india_config")["market"])
    assert result.market_cap.isna().all()
    assert result.market_cap_reason.item() == "missing_public_share_count"


def test_no_future_share_filing_can_enter_market_cap(config):
    prices, shares = inputs()
    shares.loc[0, "max_source_date"] = pd.Timestamp("2019-01-01", tz="UTC")
    with pytest.raises(ValueError, match="Future input"):
        market_cap(prices, shares, config.section("india_config")["market"])
