"""Frozen-rule peer selection using independently verified survival evidence."""

from __future__ import annotations

import pandas as pd

from prahari.config import Config
from prahari.data.manual import read_manual
from prahari.data.panel_inputs import peer_snapshot
from prahari.features.panel import select_peers


def select_panel(config: Config) -> pd.DataFrame:
    settings = config.section("india_config")["panel"]
    events = read_manual(config, "events")
    events = events.loc[events.needs_verification.eq(0)]
    if events.entity_id.duplicated().any():
        raise ValueError("Duplicate verified cases")
    if events.empty:
        raise ValueError("No verified earliest events; peer selection has not been published")
    if events[["sector", "is_financial"]].isna().any().any():
        raise ValueError("Verified events still need sourced classifications before matching peers")
    evidence = read_manual(config, "peer_survival")
    rows = []
    for case in events.to_dict(orient="records"):
        event = pd.to_datetime(case["event_date"], utc=True)
        cutoff = event - pd.DateOffset(months=3 * settings["match_lag_quarters"])
        through = event + pd.DateOffset(months=3 * settings["survival_quarters"])
        eligible = evidence.loc[evidence.matched_to.eq(case["entity_id"]) & evidence.needs_verification.eq(0)
                                & pd.to_datetime(evidence.nondefault_start, utc=True).le(cutoff)
                                & pd.to_datetime(evidence.nondefault_through, utc=True).ge(through)]
        eligible = eligible.loc[~eligible.entity_id.isin(events.entity_id)]
        selected = select_peers(peer_snapshot(config, cutoff), case["entity_id"], set(eligible.entity_id), settings)
        # Survival evidence is metadata for cohort selection, never a risk input.
        survival = eligible.sort_values("public_date").drop_duplicates("entity_id", keep="last").set_index("entity_id")
        selected["survival_source_url"] = selected.entity_id.map(survival.source_url)
        selected["survival_public_date"] = selected.entity_id.map(survival.public_date)
        rows.append(selected)
    result = pd.concat(rows, ignore_index=True)
    if result.entity_id.nunique() < settings["minimum_unique_peers"]:
        raise ValueError("Selection does not reach the required unique peer count")
    return result


def manual_peer_rows(selected: pd.DataFrame, config: Config) -> pd.DataFrame:
    result = selected.copy()
    result["source_url"] = result.source_url + ";" + result.survival_source_url
    result["public_date"] = pd.concat([pd.to_datetime(result.max_source_date, utc=True),
                                       pd.to_datetime(result.survival_public_date, utc=True)], axis=1).max(axis=1)
    result["date_is_imputed"] = result.date_is_imputed.astype(int)
    # Metadata includes future survival evidence; it is not smuggled into model inputs.
    result["period_end"] = result.matching_cutoff
    return result[config.section("manual_config")["tables"]["peers"]["columns"]]
