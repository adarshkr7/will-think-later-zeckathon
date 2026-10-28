"""Explicit counterfactual analysis, never altered production financial records."""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from prahari.data.asof import as_of
from prahari.data.firewall import assert_real, write_real_table
from prahari.features.common import MissingInput, number
from prahari.features.panel import build_features
from prahari.models.scoring import score_snapshot


def perturb_statement(values: dict, scenario: str, settings: dict) -> dict:
    """Return named interventions only; do not infer missing financial inputs.

    Accrual inflation increases PAT by the configured fraction of its absolute
    magnitude and books the same noncash receivable/equity increase. SPV shift
    tests the specified standalone total-debt field only, keeping consolidation
    unchanged. CP rollover reclassifies the configured CP amount from current
    borrowings/liabilities to long-term borrowings. An ineffective primary
    intervention is reported separately, never presented as proven robustness.
    """
    n = lambda name: number(values, name)
    if scenario == "accrual_inflation":
        delta = settings["pat_inflation_fraction"]*abs(n("pat"))
        n("cfo")
        updates = {"pat": n("pat")+delta, "receivables": n("receivables")+delta,
                   "current_assets": n("current_assets")+delta, "total_assets": n("total_assets")+delta,
                   "equity": n("equity")+delta}
        for field in ("retained_earnings", "income_continuing", "income_before_extraordinary"):
            if pd.notna(values.get(field)):
                updates[field] = n(field)+delta
        return updates
    if scenario == "spv_debt_shift":
        n("consolidated_total_debt")
        return {"total_debt": n("total_debt")*(1-settings["debt_reduction_fraction"])}
    if scenario == "cp_rollover":
        delta = n("commercial_paper")*settings["cp_rollover_fraction"]
        if delta < 0 or delta > min(n("st_borrowings"), n("current_liabilities")):
            raise MissingInput("CP reclassification exceeds reported current debt/liabilities")
        return {"commercial_paper": n("commercial_paper")-delta, "st_borrowings": n("st_borrowings")-delta,
                "lt_debt": n("lt_debt")+delta, "current_liabilities": n("current_liabilities")-delta}
    raise ValueError("Unknown registered anti-gaming scenario")


def analyze_quarter(config, features: pd.DataFrame, predictions: pd.DataFrame, sources, models: dict, arena: str) -> pd.DataFrame:
    """Only scalar scenario-analysis results leave memory; fake inputs stay tainted.

    The output is a counterfactual statistic about a real, unchanged baseline,
    not a fabricated financial observation. No intervened borrower feature row
    is written to raw, processed, outputs or the app.
    """
    assert_real(features)
    assert_real(predictions)
    cutoff = features.attrs["as_of"]
    spec = config.section("diagnostics_config")["anti_gaming"]
    basis = config.section("feature_config")["financial_basis"]
    model_settings = config.section("model_config")
    rows = []
    before = predictions.set_index("entity_id")
    observed = as_of(sources.tables["financials"], cutoff)
    for _, feature in features.loc[features.entity_id.isin(predictions.loc[predictions.tier.isin(["tier1", "tier2"]), "entity_id"])].iterrows():
        entity = feature.entity_id
        for scenario in spec["scenarios"]:
            row = {"entity_id": entity, "scoring_date": cutoff, "arena": arena, "scenario": scenario,
                   "pd_before": before.loc[entity, "pd_4q"], "pd_after": np.nan, "relative_drop": np.nan,
                   "passes_drop_limit": pd.NA, "effective_primary_input_change": pd.NA,
                   "status": "not_run", "is_counterfactual": 1, "synthetic_intervention_inputs_used": 1, "is_synthetic": 0}
            try:
                updates = perturb_statement(feature.to_dict(), scenario, spec)
                altered = copy.copy(sources)
                altered.tables = dict(sources.tables)
                altered.tables["financials"] = sources.tables["financials"].copy(deep=True)
                raw = altered.tables["financials"]
                for field, value in updates.items():
                    originals = observed.loc[observed.entity_id.eq(entity) & observed.field.eq(field)
                        & observed.period_end.eq(feature.financial_period_end) & observed.basis.eq(basis)]
                    if originals.empty:
                        raise MissingInput("missing_original_source:"+field)
                    actual = originals.iloc[-1]
                    selected = raw.entity_id.eq(entity) & raw.field.eq(field) & raw.basis.eq(basis)
                    selected &= pd.to_datetime(raw.period_end, utc=True).eq(actual.period_end)
                    selected &= pd.to_datetime(raw.public_date, utc=True).eq(actual.public_date)
                    raw.loc[selected, "value"] = value
                    raw.loc[selected, "is_synthetic"] = 1
                counter = build_features(config, cutoff, arena, sources=altered)
                group_data = as_of(altered.tables["groups"], cutoff) if "groups" in altered.tables else None
                scored, _ = score_snapshot(counter, models, model_settings, arena, groups=group_data)
                value = scored.loc[scored.entity_id.eq(entity), "pd_4q"].iloc[0]
                row["pd_after"] = value
                if pd.isna(value) or pd.isna(row["pd_before"]) or row["pd_before"] <= 0:
                    raise MissingInput("missing_or_zero_probability_endpoint")
                # Compare exactly the canonical HDM, CHS and overlay inputs.
                active = list(models["4q"].columns)+["chs_standardized", "auditor_exit_8q", "rating_watch_neg_or_inc", "rating_notch_delta_4q", "pledge_delta_4q", "delayed_filing_4q", "going_concern_flag", "caro_default_flag"]
                original = feature.reindex(active)
                changed = counter.set_index("entity_id").loc[entity].reindex(active)
                effective = not np.allclose(pd.to_numeric(original, errors="coerce"), pd.to_numeric(changed, errors="coerce"), equal_nan=True)
                drop = (row["pd_before"]-value)/row["pd_before"]
                row.update(relative_drop=drop, effective_primary_input_change=int(effective),
                           passes_drop_limit=int(drop <= spec["relative_pd_drop_limit"]),
                           status="evaluated" if effective else "no_primary_input_changed_not_a_robustness_claim")
            except (MissingInput, ValueError) as exc:
                row["status"] = "unavailable:"+str(exc)
            rows.append(row)
    return pd.DataFrame(rows)
