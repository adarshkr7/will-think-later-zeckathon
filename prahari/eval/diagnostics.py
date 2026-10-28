"""Optional registered experiments; preserve the primary model and policy."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from prahari.data.artifacts import load_hdm_models, read_features
from prahari.data.feature_inputs import load_feature_sources
from prahari.data.firewall import assert_real, write_real_table
from prahari.data.manual import read_manual
from prahari.eval.anti_gaming import analyze_quarter
from prahari.eval.drift import population_stability
from prahari.eval.india_metrics import recall_table
from prahari.eval.operating_metrics import verified_window_labels
from prahari.eval.policy_scenarios import policy_scenarios
from prahari.eval.preregistration import verify
from prahari.policy.cost import expected_cost, realized_cost
from prahari.policy.hysteresis import hysteresis_watchlist

LOG = logging.getLogger(__name__)


def run_diagnostics(config) -> None:
    registration = verify(config)
    settings, policy = config.section("diagnostics_config"), config.section("policy_config")
    sources, models = load_feature_sources(config), load_hdm_models(config)
    events, survival = read_manual(config, "events"), read_manual(config, "peer_survival")
    reference_day = config.section("feature_config")["dates"]["first_quarter"]
    drift_rows, hysteresis_rows, scenario_rows, attack_rows, statuses = [], [], [], [], []
    for arena in ("P", "U"):
        path = config.path("india_predictions") / (arena+".parquet")
        if not path.exists():
            statuses.append({"arena": arena, "component": "diagnostics", "status": "missing_registered_replay", "is_synthetic": 0})
            continue
        predictions = pd.read_parquet(path)
        assert_real(predictions)
        if not predictions.registration_hash.eq(registration).all():
            raise ValueError("Diagnostics predictions do not match the registration")
        reference = read_features(config, reference_day, arena)
        previous = {"4q": set(), "8q": set()}
        experiments = []
        first = True
        for day, quarter in predictions.groupby("scoring_date", sort=True):
            date = pd.Timestamp(day).strftime("%Y-%m-%d")
            features = read_features(config, date, arena)
            for name in settings["drift"]["features"]:
                result = population_stability(reference[name].to_numpy(), features[name].to_numpy(), settings["drift"])
                drift_rows.append({**result, "arena": arena, "feature": name, "reference_date": reference_day,
                                   "scoring_date": date, "is_synthetic": 0})
            experiment = quarter.copy()
            prior_ids = previous["4q"]
            selected_ids = set()
            for horizon in ("4q", "8q"):
                ranked = hysteresis_watchlist(quarter, previous[horizon], policy, settings["hysteresis"], probability="pd_"+horizon)
                mapping = ranked.set_index("entity_id").deep_review
                experiment["deep_review_"+horizon] = experiment.entity_id.map(mapping)
                chosen = set(ranked.loc[ranked.deep_review.eq(1), "entity_id"])
                if horizon == "4q":
                    experiment["deep_review"] = experiment.entity_id.map(mapping)
                    selected_ids = chosen
                previous[horizon] = chosen
            experiments.append(experiment)
            labels = verified_window_labels(experiment, events, survival, 4)
            union = selected_ids | prior_ids
            hysteresis_rows.append({"arena": arena, "scoring_date": date, "metric_type": "quarter_cost_turnover",
                "turnover_jaccard": len(selected_ids ^ prior_ids)/len(union) if not first and union else (0. if not first else np.nan),
                "expected_cost": expected_cost(experiment.pd_4q.to_numpy(), experiment.deep_review.to_numpy(), policy),
                "realized_cost": realized_cost(labels.to_numpy(), experiment.deep_review.to_numpy(), policy),
                "needs_verification": int(labels.isna().any() or experiment.pd_4q.isna().any()),
                "interpretation": "separate_hysteresis_experiment_not_primary", "is_synthetic": 0})
            first = False
            scenarios = policy_scenarios(quarter, verified_window_labels(quarter, events, survival, 4), policy, settings["scenarios"])
            scenario_rows.append(scenarios.assign(arena=arena, scoring_date=date))
            attacks = analyze_quarter(config, features, quarter, sources, models, arena)
            if not attacks.empty:
                attack_rows.append(attacks)
                if attacks.passes_drop_limit.eq(0).any():
                    LOG.warning("Anti-gaming relative-drop check failed in %s %s; original results retained", arena, date)
            LOG.info("Diagnostics %s %s rows=%s attacks=%s missing_probabilities=%s", arena, date, len(quarter), len(attacks), int(quarter.pd_4q.isna().sum()))
        if experiments:
            recall = recall_table(pd.concat(experiments, ignore_index=True), events, config.section("model_config")["evaluation"], arena)
            hysteresis_rows.extend(recall.assign(metric_type="strict_lead_recall", interpretation="separate_hysteresis_experiment_not_primary").to_dict(orient="records"))
        statuses.append({"arena": arena, "component": "diagnostics", "status": "registered_experiments_completed", "is_synthetic": 0})
    for key, frames in [("drift", drift_rows), ("hysteresis", hysteresis_rows), ("diagnostics_status", statuses)]:
        if frames:
            write_real_table(pd.DataFrame(frames), config.path(key))
    for key, frames in [("policy_scenarios", scenario_rows), ("anti_gaming", attack_rows)]:
        if frames:
            write_real_table(pd.concat(frames, ignore_index=True), config.path(key))
