import copy

import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.data.feature_inputs import FeatureSources
from prahari.features.panel import build_features


@pytest.fixture
def sources(config):
    row = pd.read_csv(FIXTURES / "forensic.csv").iloc[0].to_dict()
    common = {"entity_id": row["entity_id"], "public_date": "2019-09-30", "source_doc": "fixture://financial",
              "date_is_imputed": 0, "needs_verification": 0, "is_synthetic": 1}
    records = []
    for field, value in row.items():
        if field in config.section("manual_config")["tables"]["annual_financials"]["numeric"] or "_prev" in field:
            pieces = field.split("_prev")
            lag = int(pieces[1]) if len(pieces) > 1 else 0
            records.append(dict(common, field=pieces[0], value=value, period_end=f"{2019-lag}-03-31", basis="standalone"))
    market = pd.read_csv(FIXTURES / "feature_market.csv")
    entities = pd.DataFrame([dict(common, name="Fixture borrower", symbols="FIX_A", sector="fixture_sector", is_financial=0,
                                  period_end="2019-03-31", source_url="fixture://metadata")])
    shares = pd.DataFrame([dict(common, field="shares_outstanding", value=12, period_end="2019-03-31")])
    indices = pd.DataFrame(columns=["entity_id", "period_end", "public_date", "source_url", "close", "date_is_imputed", "needs_verification", "is_synthetic"])
    tables = {"financials": pd.DataFrame(records), "market": market, "entities": entities, "shares": shares, "indices": indices}
    for key, name in (("pledges", "shareholding"), ("ratings", "rating_actions"), ("governance", "governance_events"), ("nbfc", "nbfc_metrics"), ("fx", "fx_rates")):
        tables[key] = pd.DataFrame(columns=config.section("manual_config")["tables"][name]["columns"])
    return FeatureSources(tables, ("FIX_A",))


def test_feature_pipeline_uses_only_sources_before_cutoff(config, sources):
    first = build_features(config, "2019-10-01", "P", sources=sources)
    truncated = copy.deepcopy(sources)
    for name, table in truncated.tables.items():
        truncated.tables[name] = table.loc[pd.to_datetime(table.public_date, utc=True).lt(pd.Timestamp("2019-10-01", tz="UTC"))]
    second = build_features(config, "2019-10-01", "P", sources=truncated)
    pd.testing.assert_frame_equal(first, second)
    assert first.max_source_date.lt(pd.Timestamp("2019-10-01", tz="UTC")).all()
    assert first.close.item() == 10
    assert first.market_cap.item() == 120
    assert first.z_classic.item() == pytest.approx(2.91)
    assert pd.isna(first.auditor_exit_8q.item())
    assert first.auditor_exit_8q__reason.item() == "coverage_unknown"
    assert first.is_synthetic.item() == 1


def test_missing_fiscal_year_is_not_replaced_with_nearest_observation(config, sources):
    table = sources.tables["financials"]
    sources.tables["financials"] = table.loc[~table.period_end.eq("2018-03-31")]
    result = build_features(config, "2019-10-01", "P", sources=sources)
    assert pd.isna(result.sales_growth.item())
    assert result.sales_growth__reason.item() == "missing:revenue_prev1"


def test_consolidated_source_taint_cannot_escape_through_standalone_feature_join(config, sources):
    for name, table in sources.tables.items():
        sources.tables[name] = table.assign(is_synthetic=0)
    row = sources.tables["financials"].loc[lambda frame: frame.field.eq("total_assets") & frame.period_end.eq("2019-03-31")].iloc[0].copy()
    row["basis"], row["field"], row["value"], row["is_synthetic"] = "consolidated", "total_debt", 60, 1
    sources.tables["financials"] = pd.concat([sources.tables["financials"], row.to_frame().T], ignore_index=True)
    result = build_features(config, "2019-10-01", "P", sources=sources)
    assert result.is_synthetic.item() == 1


def test_batch_history_cache_preserves_exact_quarter_ends(config, sources, monkeypatch):
    original = sources.snapshot
    seen = []
    def snapshot(config, day, arena):
        seen.append(pd.Timestamp(day))
        return original(config, day, arena)
    monkeypatch.setattr(sources, "snapshot", snapshot)
    cache = {}
    build_features(config, "2019-06-30", "P", sources=sources, history_cache=cache)
    assert pd.Timestamp("2019-03-31", tz="UTC") in seen
    assert pd.Timestamp("2019-03-30", tz="UTC") not in seen
    build_features(config, "2019-09-30", "P", sources=sources, history_cache=cache)
    assert len(seen) == 5
