import json
from pathlib import Path

import pandas as pd
import pytest

from prahari.data.asof import as_of
from prahari.eval.market_coverage import equity_calendar, market_coverage


def inputs():
    data = json.loads((Path(__file__).parent / "fixtures" / "equity_sessions.json").read_text())
    return {name: pd.DataFrame(rows) for name, rows in data.items()}


def test_gold_only_session_is_not_a_missing_company_quote():
    data = inputs()
    raw = as_of(data["calendar"], "2013-01-01")
    scoped = equity_calendar(raw, as_of(data["exceptions"], "2013-01-01"))
    result = market_coverage(data["windows"], data["prices"], scoped)
    assert raw.is_trading_day.tolist() == [1, 0, 1]
    assert result.complete.item() == 1
    assert result.expected_sessions.item() == 1
    assert result.excluded_non_equity_sessions.item() == 1
    assert result.equity_scope_source_url.item() == "fixture://gold-only-session"
    assert result.is_synthetic.item() == 1


def test_unexpected_company_quote_is_not_hidden_by_scope():
    data = inputs()
    scoped = equity_calendar(as_of(data["calendar"], "2013-01-01"), as_of(data["exceptions"], "2013-01-01"))
    extra = data["prices"].assign(period_end="2012-11-11")
    result = market_coverage(data["windows"], pd.concat([data["prices"], extra]), scoped)
    assert result.complete.item() == 0
    assert result.unexpected_sessions.item() == 1


def test_scope_requires_dated_positive_evidence():
    data = inputs()
    with pytest.raises(ValueError, match="as_of"):
        equity_calendar(data["calendar"], data["exceptions"])
    exceptions = data["exceptions"].assign(public_date="2014-01-01")
    scoped = equity_calendar(as_of(data["calendar"], "2013-01-01"), as_of(exceptions, "2013-01-01"))
    assert scoped.is_equity_trading_day.tolist() == [1, 0, 1]
