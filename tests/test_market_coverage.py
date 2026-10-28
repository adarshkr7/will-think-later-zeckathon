import pandas as pd

from prahari.eval.market_coverage import market_coverage


def test_missing_calendar_does_not_reduce_the_coverage_denominator():
    windows = pd.DataFrame([{"entity_id": "FIX_A", "start": "2018-09-28", "end": "2018-09-30", "is_synthetic": 1}])
    prices = pd.DataFrame([{"entity_id": "FIX_A", "period_end": "2018-09-28", "needs_verification": 0, "is_synthetic": 1}])
    result = market_coverage(windows, prices, pd.DataFrame())
    assert result.complete.item() == 0
    assert result.expected_sessions.isna().all()
    calendar = pd.DataFrame({"period_end": ["2018-09-28", "2018-09-29", "2018-09-30"],
                             "is_trading_day": [1, 0, 0], "needs_verification": 0, "is_synthetic": 1,
                             "source_url": "fixture://calendar"})
    result = market_coverage(windows, prices, calendar)
    assert result.complete.item() == 1
    assert result.expected_sessions.item() == 1
    assert result.is_synthetic.item() == 1
