import json
from pathlib import Path

import pandas as pd
import pytest

from prahari.data.annual_intervals import reconcile_annual_flows
from prahari.data.asof import as_of
from prahari.data.firewall import write_real_table

FIXTURES = Path(__file__).parent / "fixtures"


def inputs():
    table = pd.read_csv(FIXTURES / "annual_intervals.csv")
    rule = json.loads((FIXTURES / "annual_reconciliation.json").read_text())
    return table, rule


def test_signed_annual_reconciliation_preserves_units_losses_and_latest_publication(config, tmp_path):
    table, rule = inputs()
    units = config.section("india_config")["financials"]["unit_multipliers"]
    annual, audit = reconcile_annual_flows(table, [rule], units, "2016-03-02")
    values = annual.set_index("field").numeric_value
    # 150.25 INR - 0.000501 lakh INR = 100.15 INR; -15 lakh - (-5 lakh) = -10 lakh.
    assert values["revenue"] == pytest.approx(100.15)
    assert values["pat"] == -1_000_000
    assert pd.to_datetime(annual.public_date, utc=True).eq(pd.Timestamp("2016-03-01", tz="UTC")).all()
    assert annual.source_doc.str.contains("fixture://extended#page=1;fixture://prefix#page=2", regex=False).all()
    assert annual.is_synthetic.eq(1).all() and audit.is_synthetic.eq(1).all()
    with pytest.raises(ValueError, match="Synthetic"):
        write_real_table(annual, tmp_path / "forbidden.csv")
    assert not (tmp_path / "forbidden.csv").exists()


def test_reconciliation_cannot_reveal_later_extended_report(config):
    table, rule = inputs()
    annual, audit = reconcile_annual_flows(table, [rule],
                                         config.section("india_config")["financials"]["unit_multipliers"],
                                         "2016-03-01")
    assert annual.empty
    assert audit.numeric_value.isna().all()
    assert audit.missing_reason.eq("missing_visible_interval_operand").all()


@pytest.mark.parametrize("change", ["gap", "overlap", "wrong_target_year"])
def test_incomplete_or_double_counted_years_are_rejected(config, change):
    table, rule = inputs()
    if change == "gap":
        table.loc[table.series_id.eq("prefix"), "period_end"] = "2014-11-30"
    elif change == "overlap":
        rule["components"].append(dict(rule["components"][0]))
    else:
        rule["fy_end"] = "2015-09-30"
    with pytest.raises(ValueError, match="exactly one trailing year"):
        reconcile_annual_flows(table, [rule],
                               config.section("india_config")["financials"]["unit_multipliers"],
                               "2016-03-02")


def test_same_end_different_flow_lengths_are_distinct_observations():
    table, _ = inputs()
    original = table.loc[table.series_id.eq("extended") & table.field.eq("revenue")]
    other = original.assign(period_start="2015-01-01", series_id="annual")
    visible = as_of(pd.concat([original, other], ignore_index=True), "2016-03-02")
    assert len(visible) == 2
