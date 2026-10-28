"""Prepare an offline review bundle without inventing an unregistered replay."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from prahari.config import Config
from prahari.data.artifacts import read_features
from prahari.data.firewall import assert_real, write_real_table
from prahari.data.manual import read_manual
from prahari.eval.preregistration import verify
from prahari.explain.templates import case_unavailable, memo
from prahari.policy.threshold import bayes_threshold


def build_bundle(config: Config) -> dict:
    cases = read_manual(config, "events")
    write_real_table(cases, config.path("case_catalog"))
    registered = False
    registration_reason = "Pre-registration and accepted panel evidence are required before scored replay."
    if config.path("preregistration_lock").exists():
        try:
            verify(config)
            registered = True
        except (ValueError, RuntimeError) as exc:
            registration_reason = str(exc)
    frames, details = [], []
    for path in sorted(config.path("feature_cache").glob("*/*.parquet")):
        arena, day = path.parent.name, path.stem
        features = read_features(config, day, arena)
        reasons = [name for name in features if name.endswith("__reason")]
        snapshot = features[["entity_id", "name", "symbols", "sector", "scoring_date", "arena", "max_source_date", "is_synthetic"]].copy()
        snapshot["quarter"] = day
        snapshot["observed_close"] = features.close
        snapshot["known_features"] = features[reasons].eq("").sum(axis=1)
        snapshot["missing_features"] = features[reasons].ne("").sum(axis=1)
        snapshot["score_status"], snapshot["tier"] = "readiness_only_unregistered", "unscored"
        snapshot["pd_4q"], snapshot["pd_8q"], snapshot["rank"] = np.nan, np.nan, np.nan
        prediction_path = config.path("india_replay") / arena / (day + ".parquet")
        if registered and prediction_path.exists():
            predictions = pd.read_parquet(prediction_path)
            assert_real(predictions)
            if not predictions.registration_hash.eq(verify(config)).all():
                raise ValueError("Replay artifact registration differs from current protocol")
            snapshot = snapshot.drop(columns=["pd_4q", "pd_8q", "rank", "tier", "score_status"]).merge(
                predictions[["entity_id", "pd_4q", "pd_8q", "rank", "tier"]], on="entity_id", validate="one_to_one")
            snapshot["score_status"] = np.where(snapshot.pd_4q.notna(), "registered_scored", "registered_missing_inputs")
        # Current catalog names are display labels only and never model inputs.
        labels = cases.set_index("entity_id")["name"]
        snapshot["name"] = snapshot.name.fillna(snapshot.entity_id.map(labels))
        snapshot["name_basis"] = "historical_metadata_or_retrospective_catalog_label"
        snapshot["memo_markdown"] = [memo(row, [], []) if row["score_status"] != "registered_scored" else "" for row in snapshot.to_dict(orient="records")]
        frames.append(snapshot)
        for reason_column in reasons:
            field = reason_column.removesuffix("__reason")
            detail = features[["entity_id", "scoring_date", "arena", "max_source_date", "is_synthetic"]].copy()
            detail["feature"] = field
            detail["value"] = pd.to_numeric(features[field], errors="coerce") if field in features else np.nan
            detail["reason"] = features[reason_column]
            details.append(detail)
    snapshots = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["entity_id", "quarter", "arena", "is_synthetic"])
    detail_table = pd.concat(details, ignore_index=True) if details else pd.DataFrame(columns=["entity_id", "feature", "value", "reason", "is_synthetic"])
    write_real_table(snapshots, config.path("app_snapshots"))
    write_real_table(detail_table, config.path("app_features"))
    config.path("case_cards").mkdir(parents=True, exist_ok=True)
    for row in cases.to_dict(orient="records"):
        target = config.path("case_cards") / (row["entity_id"] + ".md")
        if not registered:
            target.write_text(case_unavailable(row, registration_reason), encoding="utf-8")
    policy = config.section("policy_config")
    parameters = [{"parameter": key, "value": policy[key], "is_synthetic": 0} for key in ("cost_fn", "cost_fp", "alert_frac", "tier1_pd")]
    parameters.append({"parameter": "tau_star", "value": bayes_threshold(policy["cost_fn"], policy["cost_fp"]), "is_synthetic": 0})
    write_real_table(pd.DataFrame(parameters), config.path("app_policy"))
    checks = pd.read_csv(config.path("panel_acceptance"))
    assert_real(checks)
    status = [
        {"component": "benchmark", "status": "development_only" if not config.path("benchmark_final_metrics").exists() else "final_evaluated", "reason": "Development results are not untouched hold-out performance."},
        {"component": "panel", "status": "accepted" if checks.passed.eq(1).all() else "incomplete", "reason": ", ".join(checks.loc[checks.passed.eq(0), "check"])},
        {"component": "features", "status": "partial_data" if not detail_table.empty and detail_table.reason.ne("").any() else "available", "reason": "Missing inputs remain explicit; existing quarter files do not imply complete coverage."},
        {"component": "registration", "status": "registered" if registered else "blocked", "reason": "" if registered else registration_reason},
        {"component": "india_evaluation", "status": "available" if registered and config.path("india_metrics").exists() else "not_run", "reason": "No unregistered performance claims."},
        {"component": "sealed_evaluation", "status": "not_opened" if not config.path("indian_sealed_ledger").exists() else "claimed", "reason": "Once-only final boundary; no sealed contents read for readiness."},
    ]
    write_real_table(pd.DataFrame(status).assign(is_synthetic=0), config.path("run_status"))
    collection = pd.read_csv(config.path("collection_status")).set_index("item")
    tests = json.loads(config.path("test_summary").read_text(encoding="utf-8")) if config.path("test_summary").exists() else {}
    def count(name):
        return int(collection.loc[name, "observed"]) if name in collection.index else None
    settings = config.section("app_config")
    root = config.path("outputs")
    def relative(key):
        return str(config.path(key).relative_to(root)).replace("\\", "/")
    has_replay = not snapshots.empty and snapshots.score_status.str.startswith("registered_").any()
    manifest = {"mode": "registered_replay" if registered and has_replay else "readiness_only", "settings": settings,
                "quarters": sorted(snapshots.quarter.unique().tolist()) if not snapshots.empty else [],
                "arenas": sorted(snapshots.arena.unique().tolist()) if not snapshots.empty else [],
                "kpis": [{"label": "Verified cases", "value": count("verified_panel_events")},
                         {"label": "Matched peers", "value": count("verified_matched_peers")},
                         {"label": "Financial fields", "value": count("verified_financial_fields")},
                         {"label": "Tests passed", "value": tests.get("passed")}],
                "calibration_images": [path.name for path in sorted(config.path("benchmark_plots").glob("*.png"))],
                "files": {key: relative(key) for key in ("app_snapshots", "app_features", "case_catalog", "run_status", "app_policy", "panel_acceptance", "collection_status", "source_catalog", "coverage_parity", "feature_coverage", "memos", "case_cards", "india_metrics", "ablations", "cost_curve", "shadow_prices", "detection_curve", "placebo", "anti_gaming", "amendments", "benchmark_development_metrics", "benchmark_final_metrics", "benchmark_plots")}}
    config.path("app_manifest").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
