import json

import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.data.asof import as_of
from prahari.data.firewall import write_real_table
from prahari.data.listings import listing_rows
from prahari.eval.market_coverage import market_coverage


def certificate(config):
    fixture = json.loads((FIXTURES / "listing_certificate.json").read_text())
    return fixture, pd.DataFrame(listing_rows(fixture["spec"], "fixture://certificate", fixture["text"],
                                            config.base["dates"]["annual_report_lag_days"],
                                            is_synthetic=fixture["is_synthetic"]))


def test_listing_certificate_does_not_backdate_its_publication(config, tmp_path):
    fixture, rows = certificate(config)
    assert rows.public_date.eq("2019-09-27T00:00:00+00:00").all()
    assert as_of(rows, "2019-09-27").empty
    assert len(as_of(rows, "2019-09-28")) == len(fixture["spec"]["exchanges"])
    with pytest.raises(ValueError, match="Synthetic"):
        write_real_table(rows, tmp_path / "forbidden.csv")
    spec = {**fixture["spec"], "listing_date": "2018-09-27"}
    with pytest.raises(ValueError, match="disagrees"):
        listing_rows(spec, "fixture://certificate", fixture["text"],
                     config.base["dates"]["annual_report_lag_days"], is_synthetic=fixture["is_synthetic"])


def test_certified_prelisting_interval_is_not_full_market_history(config):
    _, rows = certificate(config)
    fixture = json.loads((FIXTURES / "listing_coverage.json").read_text())
    windows, prices, calendar = [pd.DataFrame(fixture[key]) for key in ("windows", "prices", "calendar")]
    calendar["period_end"] = pd.to_datetime(calendar.period_end, utc=True)
    known = as_of(rows, "2019-09-28")
    result = market_coverage(windows, prices, calendar, known, exchange="nse")
    assert result.complete.item() == 1
    assert result.full_window_quote_history.item() == 0
    assert result.excluded_pre_listing_sessions.item() == 1
    assert result.expected_sessions.item() == 1
    assert result.is_synthetic.item() == 1
    unavailable = as_of(rows.assign(needs_verification=1), "2019-09-28")
    assert market_coverage(windows, prices, calendar, unavailable, exchange="nse").complete.item() == 0
    assert market_coverage(windows, prices, calendar, known, exchange="unrelated").complete.item() == 0
    assert market_coverage(windows, prices, pd.DataFrame(), known, exchange="nse").complete.item() == 0
    contradictory = pd.concat([prices, pd.DataFrame(fixture["earlier_price"])], ignore_index=True)
    conflict = market_coverage(windows, contradictory, calendar, known, exchange="nse")
    assert conflict.complete.item() == 0
    assert conflict.unexpected_sessions.item() == 1
