import io
import zipfile

import pandas as pd
import pytest

from prahari.data.asof import as_of
from prahari.data.bhavcopy import archive_url, bounded_forward_fill, parse_bhavcopy, parse_index
from conftest import FIXTURES


def test_parser_keeps_old_symbols_isin_and_synthetic_provenance(config):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("fixture.csv", (FIXTURES / "bhavcopy.csv").read_bytes())
    table = parse_bhavcopy(payload.getvalue(), "fixture://bhavcopy", config.section("india_config")["market"])
    assert set(table.entity_id) == {"FIX_ISIN_A", "FIX_ISIN_OLD"}
    assert table.is_synthetic.eq(1).all()
    assert table.public_date.eq(pd.Timestamp("2018-09-29", tz="UTC")).all()


def test_index_parser_does_not_claim_tri(config):
    table = parse_index((FIXTURES / "index.csv").read_bytes(), "fixture://index", config.section("india_config")["market"])
    assert table.return_basis.eq("price_index").all()
    assert table.is_synthetic.eq(1).all()


@pytest.mark.parametrize("column", ["CLOSE", "TOTTRDQTY"])
@pytest.mark.parametrize("token", ["", "inf", "-inf"])
def test_nse_rejects_missing_or_nonfinite_observations(config, column, token):
    frame = pd.read_csv(FIXTURES / "bhavcopy.csv", dtype=str)
    frame.loc[0, column] = token
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("fixture.csv", frame.to_csv(index=False))
    with pytest.raises(ValueError, match="Invalid market observation"):
        parse_bhavcopy(payload.getvalue(), "fixture://invalid", config.section("india_config")["market"])


@pytest.mark.parametrize("token", ["", "inf", "-inf"])
def test_index_rejects_missing_or_nonfinite_closes(config, token):
    frame = pd.read_csv(FIXTURES / "index.csv", dtype=str)
    frame.loc[0, "Closing Index Value"] = token
    with pytest.raises(ValueError, match="absent or invalid"):
        parse_index(frame.to_csv(index=False).encode(), "fixture://invalid", config.section("india_config")["market"])


def test_exchange_two_digit_year_keeps_dates_and_rejects_unreviewed_format(config):
    original = (FIXTURES / "bhavcopy_two_digit_year.csv").read_bytes()
    settings = config.section("india_config")["market"]
    for content, valid in [(original, True), (original.replace(b"13-Jul-20", b"2020/07/13"), False)]:
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w") as archive:
            archive.writestr("fixture.csv", content)
        if valid:
            table = parse_bhavcopy(payload.getvalue(), "fixture://two_digit_year", settings)
            assert table.period_end.eq(pd.Timestamp("2020-07-13", tz="UTC")).all()
            assert table.public_date.eq(pd.Timestamp("2020-07-14", tz="UTC")).all()
            assert table.is_synthetic.eq(1).all()
        else:
            with pytest.raises(ValueError, match="date format"):
                parse_bhavcopy(payload.getvalue(), "fixture://unknown_date", settings)


def test_configured_url_uses_locale_independent_month(config):
    url, filename = archive_url("2018-09-28", config.section("india_config")["market"])
    assert filename == "cm28SEP2018bhav.csv.zip"
    assert "/2018/SEP/" in url


def test_forward_fill_stops_at_five_actual_sessions(config):
    fixture = pd.read_csv(FIXTURES / "asof.csv").iloc[:1].copy()
    fixture["close"], fixture["symbol"] = 10, "FIX_A"
    fixture["period_end"] = "2018-03-30"
    table = as_of(fixture, "2018-09-30")
    sessions = pd.date_range(table.period_end.iloc[0], periods=8, freq="B")
    result = bounded_forward_fill(table, sessions, config.section("india_config")["market"]["max_forward_fill_sessions"])
    assert result.close.notna().sum() == 6
    assert result.close.iloc[6:].isna().all()
    assert result.price_is_carried.sum() == 5
