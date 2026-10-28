"""Registered public evaluation; labels are read only after verification."""

from __future__ import annotations

import pandas as pd

from prahari.data.asof import as_of
from prahari.data.firewall import assert_real, write_real_table
from prahari.data.manual import read_manual
from prahari.eval.ablation import ablation_results
from prahari.eval.detection_curve import detection_curve
from prahari.eval.india_metrics import recall_table, strict_lead_observations, clustered_recall
from prahari.eval.operating_metrics import operating_metrics, verified_window_labels
from prahari.eval.placebo import within_firm_placebo
from prahari.eval.preregistration import verify
from prahari.policy.cost import cost_curve, threshold_scan
from prahari.explain.templates import case_card


def evaluate(config) -> None:
    registration = verify(config)
    settings, policy = config.section("model_config"), config.section("policy_config")
    events, peers = read_manual(config, "events"), read_manual(config, "peers")
    survival, memberships = read_manual(config, "peer_survival"), read_manual(config, "groups")
    ratings = read_manual(config, "rating_actions")
    metrics, operating, observations, detection, placebo, curves, ablations, thresholds = [], [], [], [], [], [], [], []
    status = []
    for arena in ("P", "U"):
        source = config.path("india_predictions") / (arena + ".parquet")
        if not source.is_file():
            status.append({"arena": arena, "component": "evaluation", "status": "not_run", "reason": "No registered predictions", "is_synthetic": 0})
            continue
        predictions = pd.read_parquet(source)
        assert_real(predictions)
        if not predictions.registration_hash.eq(registration).all():
            raise ValueError("Evaluation predictions do not match the current registration")
        metrics.append(recall_table(predictions, events, settings["evaluation"], arena))
        operating.append(operating_metrics(predictions, events, survival, peers, policy, arena))
        for lead in settings["evaluation"]["recall_leads"]:
            obs = strict_lead_observations(predictions, events, lead).assign(arena=arena)
            observations.append(obs)
            # Ownership evidence is retrospective evaluation metadata, but still
            # must be published by the declared evaluation horizon.
            cutoff = config.section("feature_config")["dates"]["last_quarter"]
            groups = as_of(memberships, pd.Timestamp(cutoff, tz="UTC") + pd.Timedelta(days=1))
            groups = groups.sort_values(["period_end", "public_date"]).drop_duplicates("entity_id", keep="last")
            cluster = clustered_recall(obs, groups, settings["evaluation"]["confidence"])
            metrics.append(pd.DataFrame([{**cluster, "arena": arena, "lead_quarters": lead,
                "event_definition": "event_date", "breakdown": "corporate_group_clustered", "group": "all", "is_synthetic": 0}]))
        for case in events.loc[events.needs_verification.eq(0)].to_dict(orient="records"):
            case_observations = pd.concat(observations).loc[lambda frame: frame.arena.eq(arena) & frame.entity_id.eq(case["entity_id"])]
            history = predictions.loc[predictions.entity_id.eq(case["entity_id"])].sort_values("scoring_date")
            destination = config.path("case_cards") / arena / (case["entity_id"] + ".md")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(case_card(case, case_observations.to_dict(orient="records"), history.to_dict(orient="records")), encoding="utf-8")
        detection.append(detection_curve(predictions, events, settings["evaluation"], arena,
            rating_actions=ratings, rating_settings=config.section("feature_config")["soft"]))
        placebo.append(within_firm_placebo(predictions, events, settings["evaluation"], config.seed, arena))
        ablations.append(ablation_results(predictions, events, peers, survival, settings, policy, config.seed, arena))
        for day, quarter in predictions.groupby("scoring_date"):
            ordered = quarter.sort_values("rank", na_position="last")
            curve = cost_curve(ordered.pd_4q.to_numpy(), policy, settings["evaluation"]["shadow_extra_slots"], is_synthetic=0, ordered=True)
            curves.append(curve.assign(arena=arena, scoring_date=day))
            labels = verified_window_labels(quarter, events, survival, 4)
            thresholds.append(threshold_scan(quarter.pd_4q.to_numpy(), labels.to_numpy(), policy, is_synthetic=0).assign(arena=arena, scoring_date=day))
        status.append({"arena": arena, "component": "evaluation", "status": "registered_evaluated", "reason": "Unknown scores retained in denominators; incomplete coverage flagged", "is_synthetic": 0})
    for key, frames in [("india_metrics", metrics), ("india_operating_metrics", operating), ("india_case_observations", observations),
                        ("detection_curve", detection), ("placebo", placebo), ("ablations", ablations), ("cost_curve", curves), ("threshold_scan", thresholds)]:
        if frames:
            write_real_table(pd.concat(frames, ignore_index=True), config.path(key))
    if curves:
        combined = pd.concat(curves, ignore_index=True)
        shadow = combined.loc[combined.k.ge(combined.registered_cap) & combined.k.lt(combined.registered_cap + settings["evaluation"]["shadow_extra_slots"])]
        write_real_table(shadow, config.path("shadow_prices"))
        from prahari.eval.plots import evaluation_plot
        evaluation_plot(combined, "k", ["expected_cost"], config.path("cost_plot"), "Counterfactual review budget", "Expected decision cost")
        evaluation_plot(pd.concat(detection), "lead_quarters", ["recall", "rating_sub_ig_recall", "altman_distress_recall"], config.path("detection_plot"), "Quarters before event", "Share of verified cases")
    write_real_table(pd.DataFrame(status), config.path("evaluation_status"))
