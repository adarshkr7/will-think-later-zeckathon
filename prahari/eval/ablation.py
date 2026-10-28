"""Registered ablation variants and overlap-safe case grouping."""

import pandas as pd
import numpy as np
from scipy.special import expit

from prahari.eval.india_metrics import recall_table
from prahari.eval.operating_metrics import verified_window_labels
from prahari.models.stacker import group_oof_stacker
from prahari.policy.watchlist import build_watchlist
from prahari.policy.cost import realized_cost


def connected_case_groups(peers: pd.DataFrame) -> dict[str, str]:
    """Shared peers connect case folds, preventing an entity from leaking across CV.

    These are CV components, not claimed corporate ownership memberships.
    """
    parents = {}
    def find(value):
        parents.setdefault(value, value)
        if parents[value] != value:
            parents[value] = find(parents[value])
        return parents[value]
    for row in peers.itertuples():
        left, right = find(row.entity_id), find(row.matched_to)
        parents[max(left, right)] = min(left, right)
    return {value: find(value) for value in parents}


def ranked_baseline(features: pd.DataFrame, value: str, limit: int, *, ascending: bool) -> pd.Series:
    """Same budget and deterministic ties; missing baseline inputs do not fill slots."""
    eligible = features.loc[features[value].notna()].sort_values([value, "entity_id"], ascending=[ascending, True], kind="stable")
    return features.entity_id.isin(eligible.head(limit).entity_id).astype(int)


def ablation_results(predictions, events, peers, survival, settings, policy, seed, arena):
    """Fixed variants and nested OOF stacker, always separate from the primary."""
    frame = predictions.reset_index(drop=True).copy()
    forensic = pd.DataFrame(index=frame.index)
    for field, sign in settings["ablation"]["forensic_weights"].items():
        forensic[field] = np.nan
        for _, group in frame.groupby("scoring_date"):
            values = group[field].dropna()
            spread = values.quantile(.75) - values.quantile(.25)
            if len(values) > 1 and spread > 0:
                forensic.loc[group.index, field] = sign*(group[field]-values.median())/spread
    frame["forensic"] = forensic.mean(axis=1).where(forensic.notna().all(axis=1))
    groups = connected_case_groups(peers.loc[peers.needs_verification.eq(0)])
    case_ids = sorted(events.loc[events.needs_verification.eq(0), "entity_id"])
    for entity in case_ids:
        groups.setdefault(entity, entity)
    components = sorted(set(groups.values()))
    if components:
        import hashlib
        frame["cv_group"] = frame.entity_id.map(lambda entity: groups.get(entity, components[int(hashlib.sha256(f"{seed}:{entity}".encode()).hexdigest(), 16) % len(components)]))
    else:
        frame["cv_group"] = frame.entity_id
    summaries = []
    for horizon in ("4q", "8q"):
        frame["hdm_logit"] = frame["hdm_logit_" + horizon]
        component_names = list(settings["ablation"]["component_signs"])
        labels = verified_window_labels(frame, events, survival, int(horizon[:-1]))
        days = pd.to_datetime(frame.scoring_date, utc=True)
        train = days.ge(pd.to_datetime(settings["ablation"]["first_training_date"], utc=True)) & days.le(pd.to_datetime(settings["ablation"]["last_training_date"], utc=True))
        try:
            stacker, _ = group_oof_stacker(frame[component_names], labels.to_numpy(), frame.cv_group.to_numpy(),
                list(settings["ablation"]["component_signs"].values()), settings["ablation"], seed, train_eligible=train)
        except ValueError:
            stacker = np.full(len(frame), np.nan)
        variants = {
            "HDM_only": frame.hdm_logit,
            "HDM_forensic": frame.hdm_logit + frame.forensic,
            "HDM_forensic_CHS": frame.hdm_logit + frame.forensic + frame.chs_standardized,
            "HDM_forensic_CHS_soft": frame.hdm_logit + frame.forensic + frame.chs_standardized + frame.soft_overlay,
            "fixed_weight_baseline": frame[component_names].mean(axis=1).where(frame[component_names].notna().all(axis=1)),
            "CHS_only": frame.chs_standardized,
            "Altman_only": -frame.z_em,
            "rating_downgrade_only": frame.rating_notch_delta_4q,
            "drawdown_only": -frame.drawdown_52w,
            "stacker_ablation_only": pd.Series(np.log(np.clip(stacker, 1e-12, 1-1e-12)/(1-np.clip(stacker, 1e-12, 1-1e-12))), index=frame.index),
        }
        for name, margin in variants.items():
            rows = []
            for _, group in frame.assign(_margin=margin).groupby("scoring_date"):
                scored = group.copy()
                scored["pd_" + horizon] = expit(scored._margin)
                # These are ranking-only baselines; threshold-tier probabilities
                # are not claimed to be calibrated Indian default estimates.
                scored["hard_trigger"] = 0
                ranked = build_watchlist(scored, policy, probability="pd_" + horizon)
                ranked["deep_review_" + horizon] = ranked.deep_review
                rows.append(ranked)
            variant = pd.concat(rows, ignore_index=True)
            metrics = recall_table(variant, events, {**settings["evaluation"], "recall_leads": [int(horizon[:-1])]}, arena)
            metrics["variant"] = name
            metrics["interpretation"] = "ranking_baseline" if name != "stacker_ablation_only" else "nested_case_group_oof"
            known_labels = verified_window_labels(variant, events, survival, int(horizon[:-1]))
            metrics["realized_cost"] = realized_cost(known_labels.to_numpy(), variant.deep_review.to_numpy(), policy)
            summaries.append(metrics)
    return pd.concat(summaries, ignore_index=True) if summaries else pd.DataFrame()
