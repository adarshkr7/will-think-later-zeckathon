import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.data.asof import as_of
from prahari.data.fx import parse_release
from prahari.data.firewall import write_real_table


def test_original_release_dates_control_visibility_and_preserve_missing_rates(config, tmp_path):
    rows = parse_release((FIXTURES / "fx_release.html").read_bytes(), "fixture://original_release", "2019-01-07", config.section("fx_config"))
    assert rows.period_end.iloc[0] == "2018-12-31"
    assert rows.needs_verification.tolist() == [0, 1, 0, 0, 0]
    assert as_of(rows, "2019-01-07").empty
    assert len(as_of(rows, "2019-01-08")) == 4
    assert rows.is_synthetic.eq(1).all()
    with pytest.raises(ValueError, match="Synthetic"):
        write_real_table(rows, tmp_path / "forbidden.csv")
    with pytest.raises(ValueError, match="differs"):
        parse_release((FIXTURES / "fx_release.html").read_bytes(), "fixture://original_release", "2019-01-08", config.section("fx_config"))
