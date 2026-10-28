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
                            & sector.total_assets.gt(0) & sector.leverage.notna() & sector.needs_verification.eq(0)].copy()
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


def build_features(config, t, arena: str = "P", *, sources=None, history_cache: dict | None = None) -> pd.DataFrame:
    """Build a single dated cross-section; no Indian outcome enters a feature.

    Every source read is filtered by data.asof, including each of the four
    historical accounting snapshots used by CHS. Unknown observations stay
    missing and carry explicit reasons rather than neutral score defaults.
    """
    import numpy as np
    from prahari.data.feature_inputs import load_feature_sources
    from prahari.features.chs import chs_accounting, chs_score, market_statistics, weighted_average
    from prahari.features.common import divide, evaluate, number
    from prahari.features.forensic import forensic_features
    from prahari.features.nbfc import nbfc_features
    from prahari.features.ratios import harmonized_ratios
    from prahari.features.soft import soft_features

    sources = sources if sources is not None else load_feature_sources(config)
    settings = config.section("feature_config")
    cutoff = pd.to_datetime(t, utc=True)
    base, tables = sources.snapshot(config, cutoff, arena)
    # A batch may reuse only snapshots from its one immutable input load.
    # The default cache is local, so independent/future-deletion calls cannot
    # inherit observations from another source object.
    history_cache = {} if history_cache is None else history_cache
    history_cache[(arena, cutoff)] = base.copy()
    result = base.copy()
    result.attrs.update(base.attrs)
    source_dates = ["max_source_date"]
    def merge(frame: pd.DataFrame, name: str) -> None:
        nonlocal result
        available = [column for column in frame if column not in result or column in ("entity_id", "max_source_date", "is_synthetic")]
        frame = frame[available].rename(columns={"max_source_date": name + "_component_date", "is_synthetic": name + "_component_synthetic"})
        result = result.merge(frame, on="entity_id", how="left", validate="one_to_one")
        source_dates.append(name + "_component_date")
        result["is_synthetic"] = (result.is_synthetic.eq(1) | result[name + "_component_synthetic"].eq(1)).astype(int)
    merge(harmonized_ratios(base), "ratios")
    merge(forensic_features(base, settings), "forensic")
    prices = tables["market"].loc[tables["market"].entity_id.isin(base.entity_id)]
    merge(market_statistics(prices, tables["indices"], settings["chs"]), "market")
    merge(soft_features(base, tables["pledges"], tables["ratings"], tables["governance"], settings["soft"], coverage=tables.get("signal_coverage")), "soft")
    merge(nbfc_features(base, settings["nbfc"]), "nbfc")
    for name in ("nimta", "tlmta", "cashmta", "relsize", "mb", "price"):
        computed = [chs_accounting(record, settings["chs"])[name] for record in base.to_dict(orient="records")]
        result[name] = [value.value for value in computed]
        result[name + "__reason"] = [value.reason for value in computed]
    histories = []
    for lag in range(4):
        prior_cutoff = cutoff - pd.offsets.QuarterEnd(lag, startingMonth=3) if cutoff.is_quarter_end else cutoff - pd.DateOffset(months=3*lag)
        key = (arena, prior_cutoff)
        if key not in history_cache:
            history_cache[key] = sources.snapshot(config, prior_cutoff, arena)[0].copy()
        prior = history_cache[key].copy()
        prior["nimta_history"] = [chs_accounting(record, settings["chs"])["nimta"].value for record in prior.to_dict(orient="records")]
        histories.append(prior.set_index("entity_id"))
    averages, history_dates = [], []
    for entity in result.entity_id:
        values = [history.loc[entity, "nimta_history"] if entity in history.index else np.nan for history in histories]
        averages.append(weighted_average(values, settings["chs"]["monthly_decay"] ** 3))
        dates = [history.loc[entity, "max_source_date"] for history in histories if entity in history.index]
        history_dates.append(max((date for date in dates if pd.notna(date)), default=pd.NaT))
    result["nimtaavg"], result["nimtaavg__reason"] = [value.value for value in averages], [value.reason for value in averages]
    result["history_component_date"] = history_dates
    source_dates.append("history_component_date")
    scores = [chs_score(record, settings["chs"]) for record in result.to_dict(orient="records")]
    result["chs_score"], result["chs_score__reason"] = [value.value for value in scores], [value.reason for value in scores]
    chs = result.chs_score.dropna()
    result["chs_standardized"] = np.nan
    result["chs_center"], result["chs_scale"] = np.nan, np.nan
    result["chs_standardized__reason"] = "insufficient_cross_section_spread"
    if len(chs) > 1:
        spread = chs.quantile(.75) - chs.quantile(.25)
        if spread > 0:
            result["chs_center"], result["chs_scale"] = chs.median(), spread
            result["chs_standardized"] = (result.chs_score - chs.median()) / spread
            result.loc[result.chs_standardized.notna(), "chs_standardized__reason"] = ""
    interactions = [evaluate(lambda record=record: number(record, "pledge_pct") / 100 * number(record, "tlmta") * max(0, -number(record, "nimtaavg"))) for record in result.to_dict(orient="records")]
    result["psp_interaction"], result["psp_interaction__reason"] = [value.value for value in interactions], [value.reason for value in interactions]
    for column in source_dates:
        result[column] = pd.to_datetime(result[column], utc=True)
    result["max_source_date"] = result[source_dates].max(axis=1)
    if result.chs_standardized.notna().any():
        result.loc[result.chs_standardized.notna(), "max_source_date"] = result.max_source_date.max()
        if result.is_synthetic.eq(1).any():
            result.loc[result.chs_standardized.notna(), "is_synthetic"] = 1
    result["scoring_date"] = cutoff
    result["needs_verification"] = result.max_source_date.isna().astype(int)
    for column in result:
        if column.endswith("__reason"):
            result[column] = result[column].fillna("not_observed_before_cutoff")
    result = result.drop(columns=[column for column in result if "_component_" in column])
    result.attrs["as_of"] = cutoff.isoformat()
    if result.max_source_date.dropna().ge(cutoff).any():
        raise AssertionError("Feature provenance crossed the scoring cutoff")
    return result
