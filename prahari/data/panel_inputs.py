"""Build dated sector/asset inputs for peer selection, without outcome labels."""

from __future__ import annotations

import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.financials import financials_as_of
from prahari.data.manual import read_manual


def join_peer_snapshot(financials: pd.DataFrame, entities: pd.DataFrame) -> pd.DataFrame:
    if financials.attrs.get("as_of") != entities.attrs.get("as_of") or "as_of" not in entities.attrs:
        raise ValueError("Peer inputs require matching as_of cutoffs")
    financials = financials.loc[financials.basis.eq("standalone") & financials.field.isin(["total_assets", "total_liabilities"])].copy()
    financials["value"] = pd.to_numeric(financials.value, errors="raise")
    assets = financials.loc[financials.field.eq("total_assets")].sort_values("period_end").drop_duplicates("entity_id", keep="last")
    liabilities = financials.loc[financials.field.eq("total_liabilities"), ["entity_id", "period_end", "value", "max_source_date"]]
    liabilities = liabilities.rename(columns={"value": "total_liabilities", "max_source_date": "liability_source_date"})
    assets = assets.rename(columns={"value": "total_assets", "max_source_date": "asset_source_date"})
    values = assets.merge(liabilities, on=["entity_id", "period_end"], how="left", validate="one_to_one")
    metadata = entities.sort_values(["period_end", "public_date"]).drop_duplicates("entity_id", keep="last")
    metadata = metadata[["entity_id", "name", "symbols", "sector", "is_financial", "max_source_date", "source_url", "is_synthetic"]].rename(
        columns={"max_source_date": "metadata_source_date", "is_synthetic": "metadata_synthetic"})
    result = values.merge(metadata, on="entity_id", how="inner", validate="one_to_one")
    result["max_source_date"] = result[["asset_source_date", "liability_source_date", "metadata_source_date"]].max(axis=1)
    result["is_synthetic"] = (result.is_synthetic.eq(1) | result.metadata_synthetic.eq(1)).astype(int)
    result.attrs["as_of"] = entities.attrs["as_of"]
    return result


def peer_snapshot(config: Config, t: str | pd.Timestamp) -> pd.DataFrame:
    return join_peer_snapshot(financials_as_of(config, t), as_of(read_manual(config, "entities"), t))
