import json

import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.data.asof import as_of
from prahari.data.firewall import write_real_table
from prahari.data.session_calendar import certify_period


def inputs():
    fixture = json.loads((FIXTURES / "session_census.json").read_text())
    sessions = as_of(pd.DataFrame(fixture["sessions"]), "2018-10-02")
    claims = as_of(pd.DataFrame(fixture["claims"]), "2018-10-02")
    arguments = (pd.Timestamp(fixture["start"]), pd.Timestamp(fixture["end"]), fixture["exchange"], "fixture://census")
    return sessions, claims, arguments


def test_exact_independent_count_certifies_civil_complement_and_provenance(tmp_path):
    sessions, claims, arguments = inputs()
    calendar, status = certify_period(sessions, claims, *arguments)
    assert status["status"] == "complete_census"
    assert calendar.is_trading_day.tolist() == [1, 1, 0, 0]
    assert calendar.public_date.eq(pd.Timestamp("2018-10-01", tz="UTC")).all()
    assert calendar.source_url.str.contains("fixture://published-count;fixture://census", regex=False).all()
    with pytest.raises(ValueError, match="Synthetic"):
        write_real_table(calendar, tmp_path / "forbidden.csv")


def test_absent_archives_cannot_certify_closed_dates():
    sessions, claims, arguments = inputs()
    calendar, status = certify_period(sessions.iloc[:1], claims, *arguments)
    assert status["status"] == "incomplete_census"
    assert calendar.is_trading_day.eq(1).all()
    hidden = as_of(claims.drop(columns="max_source_date"), "2018-10-01")
    calendar, status = certify_period(sessions, hidden, *arguments)
    assert status["status"] == "count_source_missing"
    assert calendar.is_trading_day.eq(1).all()


def test_count_disagreements_excess_and_wrong_scope_cannot_certify():
    sessions, claims, arguments = inputs()
    conflict = pd.concat([claims, claims.assign(field="source_count_B", expected_count=3)], ignore_index=True)
    conflict.attrs.update(claims.attrs)
    calendar, status = certify_period(sessions, conflict, *arguments)
    assert status["status"] == "count_source_conflict"
    assert calendar.is_trading_day.eq(1).all()
    calendar, status = certify_period(sessions, claims.assign(expected_count=1), *arguments)
    assert status["status"] == "excess_observations"
    assert calendar.is_trading_day.eq(1).all()
    calendar, status = certify_period(sessions, claims.assign(period_start="2018-09-26"), *arguments)
    assert status["status"] == "count_source_missing"
    assert calendar.is_trading_day.eq(1).all()
    with pytest.raises(ValueError, match="non-integral"):
        certify_period(sessions, claims.assign(expected_count=2.5), *arguments)
