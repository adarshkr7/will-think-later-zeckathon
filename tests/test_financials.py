import pandas as pd

from prahari.data.asof import as_of
from prahari.data.financials import normalize_financials
from prahari.data.quality import accounting_coverage
from conftest import FIXTURES


def test_field_specific_publication_lags_and_firewall(config):
    source = pd.read_csv(FIXTURES / "financials.csv")
    normalized = normalize_financials(source, config.section("india_config"), config.base["dates"],
                                       ["total_assets", "total_liabilities", "equity", "cfo"])
    assert normalized.is_synthetic.eq(1).all()
    dates = normalized.set_index("field").public_date
    end = pd.Timestamp("2018-03-31", tz="UTC")
    assert dates.total_assets == end + pd.Timedelta(days=config.base["dates"]["results_lag_days"])
    assert dates.cfo == end + pd.Timedelta(days=config.base["dates"]["annual_report_lag_days"])
    assert "cfo" not in set(as_of(normalized, "2018-07-01").field)
    assert normalized.date_is_imputed.eq(1).all()


def test_actual_annual_report_date_and_unknown_field(config):
    source = pd.read_csv(FIXTURES / "financials.csv")
    source["annual_report_public_date"] = "2018-11-01"
    source["cfo"] = float("nan")
    normalized = normalize_financials(source, config.section("india_config"), config.base["dates"], ["cfo"])
    assert normalized.value.isna().all()
    assert normalized.needs_verification.eq(1).all()
    assert normalized.public_date.item() == pd.Timestamp("2018-11-01", tz="UTC")
    assert normalized.date_is_imputed.item() == 0


def test_accounting_coverage_preserves_missingness_and_flags(config):
    source = pd.read_csv(FIXTURES / "financials.csv").rename(columns={"fy_end": "period_end"})
    tolerance = config.section("manual_config")["validation"]["accounting_tolerance"]
    assert accounting_coverage(source, tolerance).identity_status.item() == "pass"
    source["equity"] = float("nan")
    result = accounting_coverage(source, tolerance)
    assert result.identity_status.item() == "missing_inputs"
    assert result.identity_relative_error.isna().all()
    assert result.is_synthetic.eq(1).all()
