import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.data.asof import as_of
from prahari.data.firewall import write_real_table
from prahari.data.shareholding_import import parse_shareholding


def test_original_share_counts_and_denominators_preserve_precise_publication(config, tmp_path):
    payload = (FIXTURES / "shareholding.xml").read_bytes()
    public = pd.Timestamp("2018-04-20T17:10:05Z")
    settings = config.section("shareholding_config")
    shares, holding = parse_shareholding(payload, "FIX_SHP", "2018-03-31", public, "fixture://shp", "fixture://index", settings)
    assert shares["shares_outstanding"] == 110
    assert holding["promoter_holding_pct"] == 80
    assert holding["promoter_pledged_pct_of_promoter"] == 40
    table = pd.DataFrame([shares])
    assert as_of(table, public).empty
    assert len(as_of(table, public+pd.Timedelta(seconds=1))) == 1
    mixed = pd.DataFrame([{**shares, "public_date": "2018-04-19"}, shares])
    assert as_of(mixed, public).public_date.item() == pd.Timestamp("2018-04-19", tz="UTC")
    with pytest.raises(ValueError, match="Synthetic"):
        write_real_table(table, tmp_path / "forbidden.csv")
    with pytest.raises(ValueError, match="identity"):
        parse_shareholding(payload, "FIX_OTHER", "2018-03-31", public, "fixture://shp", "fixture://index", settings)
    missing = payload.replace(b'<s:NumberOfShares contextRef="dr">10</s:NumberOfShares>', b'')
    _, incomplete = parse_shareholding(missing, "FIX_SHP", "2018-03-31", public, "fixture://shp", "fixture://index", settings)
    assert pd.isna(incomplete["promoter_holding_pct"])
    assert incomplete["needs_verification"] == 1
