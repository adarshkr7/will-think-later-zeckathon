"""Registered historical scoring; no fit or threshold tuning is performed."""

from __future__ import annotations

import pandas as pd

from prahari.config import Config
from prahari.data.artifacts import load_hdm_models, read_features
from prahari.data.feature_inputs import load_feature_sources
from prahari.data.asof import as_of
from prahari.data.firewall import write_real_table
from prahari.eval.preregistration import verify
from prahari.models.scoring import score_snapshot
from prahari.policy.watchlist import build_watchlist
from prahari.explain.engine import explain_snapshot
from prahari.explain.evidence_chain import export_chains


def replay(config: Config, arena: str) -> pd.DataFrame:
    lock_hash = verify(config)
    models = load_hdm_models(config)
    sources = load_feature_sources(config)
    settings = config.section("model_config")
    policy = config.section("policy_config")
    dates = config.section("feature_config")["dates"]
    results = []
    previous_features, previous_scores = None, None
    for day in pd.date_range(dates["first_quarter"], dates["last_quarter"], freq="QE-MAR"):
        features = read_features(config, str(day.date()), arena)
        scored, designs = score_snapshot(features, models, settings, arena, groups=as_of(sources.tables["groups"], day))
        watchlist = build_watchlist(scored, policy)
        research_8q = build_watchlist(scored, policy, probability="pd_8q").set_index("entity_id")
        for field in ("deep_review", "rank", "tier"):
            watchlist[field + "_8q"] = watchlist.entity_id.map(research_8q[field])
        watchlist["deep_review_4q"] = watchlist.deep_review
        watchlist["registration_hash"] = lock_hash
        watchlist["evaluation_mode"] = "registered_primary"
        explain_snapshot(config, features, watchlist, models, designs, sources)
        if previous_features is not None:
            export_chains(config, sources, previous_features, previous_scores, features, watchlist, models, arena)
        write_real_table(watchlist, config.path("india_replay") / arena / f"{day:%Y-%m-%d}.parquet")
        results.append(watchlist)
        previous_features, previous_scores = features, watchlist
    result = pd.concat(results, ignore_index=True)
    write_real_table(result, config.path("india_predictions") / f"{arena}.parquet")
    return result
