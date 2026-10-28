import pandas as pd

from prahari.data.asof import as_of
from prahari.data.panel_inputs import join_peer_snapshot
from conftest import FIXTURES


def test_peer_assets_and_liabilities_are_same_period_and_dated():
    source = pd.read_csv(FIXTURES / "peer_snapshot.csv")
    fields = source.melt(id_vars=[c for c in source if c not in ("total_assets", "total_liabilities")],
                         value_vars=["total_assets", "total_liabilities"], var_name="field", value_name="value")
    fields["basis"] = "standalone"
    entities = source.drop(columns=["total_assets", "total_liabilities"]).assign(
        name=source.entity_id, symbols=source.entity_id, source_url="fixture://entity")
    financials = as_of(fields, "2017-01-01")
    metadata = as_of(entities, "2017-01-01")
    result = join_peer_snapshot(financials, metadata)
    assert len(result) == len(source)
    assert result.attrs["as_of"] == financials.attrs["as_of"]
    assert result.is_synthetic.eq(1).all()
    assert result.loc[result.entity_id.eq("FIX_CASE"), "total_assets"].item() == 100
    fields.loc[fields.field.eq("total_liabilities"), "period_end"] = "2015-03-31"
    result = join_peer_snapshot(as_of(fields, "2017-01-01"), metadata)
    assert result.total_liabilities.isna().all()
