"""Phase 2 peer matching. No model fitting or outcome-dependent risk features."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def select_peers(snapshot: pd.DataFrame, focal_entity_id: str, eligible_ids: set[str], settings: dict) -> pd.DataFrame:
    """Same-sector asset-distance selection with a stressed-survivor quota.

    Input must be a snapshot returned by as_of at event-minus-12Q. Eligibility
    is independently verified survival evidence supplied by evaluation/data
    collection, never a model prediction. Missing evidence is not survival.
    """
    if "as_of" not in snapshot.attrs:
        raise ValueError("Peer selection requires an as_of snapshot")
    if snapshot.entity_id.duplicated().any():
        raise ValueError("Peer snapshot must contain one row per entity")
    cutoff = pd.to_datetime(snapshot.attrs["as_of"], utc=True)
    if not pd.to_datetime(snapshot.max_source_date, utc=True).lt(cutoff).all():
        raise ValueError("Peer inputs contain future sources")
    focal = snapshot.loc[snapshot.entity_id.eq(focal_entity_id)]
    if len(focal) != 1:
        raise ValueError("Missing focal company asset snapshot")
    focal = focal.iloc[0]
    if pd.isna(focal.total_assets) or focal.total_assets <= 0 or pd.isna(focal.sector):
        raise ValueError("Focal assets/sector are unverified")
    # Sector-wide leverage threshold is calculated before survivor filtering.
    sector = snapshot.loc[snapshot.sector.eq(focal.sector) & snapshot.is_financial.eq(focal.is_financial)].copy()
    valid = sector.total_assets.gt(0) & sector.total_liabilities.ge(0)
    sector["leverage"] = (sector.total_liabilities / sector.total_assets.where(valid)).where(valid)
    threshold = sector.leverage.quantile(settings["stressed_quantile"])
    candidates = sector.loc[sector.entity_id.isin(eligible_ids) & sector.entity_id.ne(focal_entity_id)
                            & sector.total_assets.gt(0) & sector.needs_verification.eq(0)].copy()
    candidates["asset_distance"] = (candidates.total_assets - focal.total_assets).abs()
    candidates["is_stressed_survivor"] = candidates.leverage.ge(threshold).astype(int)
    candidates = candidates.sort_values(["asset_distance", "entity_id"], kind="stable")
    count = settings["peers_per_case"]
    stressed_count = math.ceil(count * settings["stressed_fraction"])
    stressed = candidates.loc[candidates.is_stressed_survivor.eq(1)].head(stressed_count)
    if len(stressed) < stressed_count or len(candidates) < count:
        raise ValueError("Insufficient verified same-sector peers/stressed survivors")
    remaining = candidates.loc[~candidates.entity_id.isin(stressed.entity_id)].head(count - len(stressed))
    result = pd.concat([stressed, remaining]).sort_values(["asset_distance", "entity_id"], kind="stable")
    result["matched_to"] = focal_entity_id
    result["selection_rule_version"] = settings["selection_rule_version"]
    result["matching_cutoff"] = cutoff
    return result.reset_index(drop=True)
