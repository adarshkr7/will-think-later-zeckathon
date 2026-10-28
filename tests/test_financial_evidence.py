import pandas as pd
import pytest

from prahari.data.asof import as_of
from prahari.data.financials import combine_financial_evidence, normalize_evidence, normalize_financials
from conftest import FIXTURES


def test_explicit_units_and_annual_filing_lag(config):
    source = pd.read_csv(FIXTURES / "financial_evidence.csv")
    result = normalize_evidence(source, config.section("india_config"), config.base["dates"])
    assert result.value.item() == 1000000000  # 100 crore × 10,000,000 INR/crore.
    assert result.unit.item() == "INR"
    assert result.public_date.item() == pd.Timestamp("2018-03-31", tz="UTC") + pd.Timedelta(days=config.base["dates"]["annual_report_lag_days"])
    assert result.is_synthetic.eq(1).all()


def test_unknown_units_never_assume_currency(config):
    source = pd.read_csv(FIXTURES / "financial_evidence.csv")
    source["unit"] = "unverified_unit"
    result = normalize_evidence(source, config.section("india_config"), config.base["dates"])
    assert result.value.isna().all()
    assert result.unit.isna().all()
    assert result.needs_verification.item() == 1


def test_verified_field_does_not_upgrade_other_partial_fields(config):
    wide_source = pd.read_csv(FIXTURES / "financials.csv")
    wide_source["needs_verification"] = 1
    wide = normalize_financials(wide_source, config.section("india_config"), config.base["dates"], ["total_assets", "cfo"])
    field_source = pd.read_csv(FIXTURES / "financial_evidence.csv")
    evidence = normalize_evidence(field_source, config.section("india_config"), config.base["dates"])
    result = as_of(combine_financial_evidence(wide, evidence), "2019-01-01")
    assert result.field.tolist() == ["total_assets"]
    assert result.value.item() == 1000000000


def test_conflicting_simultaneous_evidence_fails(config):
    source = pd.read_csv(FIXTURES / "financial_evidence.csv")
    first = normalize_evidence(source, config.section("india_config"), config.base["dates"])
    second = first.copy()
    second["value"] = 1
    with pytest.raises(ValueError, match="Contradictory"):
        combine_financial_evidence(first, second)


def test_comparative_restatement_uses_later_source_report_date(config):
    source = pd.read_csv(FIXTURES / "financial_evidence.csv")
    source["fy_end"] = source["period_end"] = "2017-03-31"
    result = normalize_evidence(source, config.section("india_config"), config.base["dates"])
    assert result.public_date.item() == pd.Timestamp("2018-03-31", tz="UTC") + pd.Timedelta(days=config.base["dates"]["annual_report_lag_days"])
    assert as_of(result, "2017-12-31").empty
