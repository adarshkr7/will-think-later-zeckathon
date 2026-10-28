import io
import zipfile

import pandas as pd

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
