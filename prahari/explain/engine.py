"""Frozen-model driver exports; no explanation model is fitted in India."""

from __future__ import annotations

import numpy as np
import pandas as pd

from prahari.data.evidence import evidence_items
from prahari.data.firewall import write_real_table
from prahari.explain.attribution import calibrated_margin_allocation, linear_chs_allocation, marginal_pd_points, reconcile
from prahari.explain.pillars import pillar_contributions
from prahari.explain.templates import memo
from prahari.models.primary import soft_contributions


def explain_snapshot(config, features, watchlist, models, designs, sources) -> pd.DataFrame:
    """Export exact logit drivers and deterministic memos for scored rows only."""
    settings = config.section("model_config")
    primary, spec = settings["primary"], settings["explanation"]
    chs = config.section("feature_config")["chs"]
    pillars = config.section("pillars_config")
    quarter = pd.Timestamp(features.attrs["as_of"]).strftime("%Y-%m-%d")
    watchlist = watchlist.set_index("entity_id").loc[features.entity_id].reset_index()
    watchlist.index = features.index
    arena = str(watchlist.arena.iloc[0])
    all_rows = []
    for horizon, model in models.items():
        valid = watchlist[f"pd_{horizon}"].notna()
        nonfinancial = valid & features.is_financial.eq(0)
        bases, allocations = {}, {}
        if nonfinancial.any():
            design = designs[horizon].loc[nonfinancial]
            raw = model.pipeline.named_steps["model"].predict(design, pred_contrib=True)
            base, terms = calibrated_margin_allocation(raw, model.calibrator, model.training_prior,
                primary["priors"][horizon], primary["probability_epsilon"], spec["calibration_difference_step"])
            for position, index in enumerate(design.index):
                bases[index] = float(primary["hdm_weight"] * base[position])
                allocations[index] = dict(zip(design.columns, primary["hdm_weight"] * terms[position], strict=True))
        for index in watchlist.index[valid]:
            values, scored = features.loc[index].to_dict(), watchlist.loc[index].to_dict()
            if index in bases:
                intercept, contributions = bases[index], allocations[index]
            else:
                from scipy.special import logit
                intercept = float(logit(primary["priors"][horizon]) - primary["nbfc_logit_scale"] * primary["nbfc_center"])
                contributions = {"nbfc_score": primary["nbfc_logit_scale"] * values["nbfc_score"]}
            chs_base, chs_terms = linear_chs_allocation(values, chs, values["chs_center"], values["chs_scale"], primary["chs_weight"])
            intercept += chs_base
            for name, value in chs_terms.items():
                contributions[name] = contributions.get(name, 0) + value
            contributions.update(soft_contributions(values, primary, arena))
            reconcile(intercept, contributions, scored[f"logit_{horizon}"], spec["tolerance"])
            pd_points = marginal_pd_points(scored[f"logit_{horizon}"], contributions)
            aggregate = pillar_contributions(contributions, pillars)
            drivers = []
            for name, contribution in contributions.items():
                display_value = values.get(name, np.nan)
                if name == "pledge_jump":
                    display_value = float(values["pledge_delta_4q"] > primary["pledge_jump_pp"])
                if name == "audit_default_or_going_concern":
                    display_value = float(values["caro_default_flag"] == 1 or values["going_concern_flag"] == 1)
                driver = {"feature": name, "value": display_value, "logit_contribution": contribution,
                          "pd_points": pd_points[name], "pillar": pillars["features"][name.removesuffix("__missing")]}
                drivers.append(driver)
                all_rows.append({**driver, "entity_id": values["entity_id"], "scoring_date": quarter, "arena": arena,
                                 "horizon": horizon, "intercept": intercept, "final_logit": scored[f"logit_{horizon}"],
                                 "allocation_method": "calibration_path_proportional_native_margin_shap",
                                 "is_synthetic": int(values["is_synthetic"])})
            if horizon == "4q" and scored["deep_review"] == 1:
                evidence = evidence_items(sources, values["entity_id"], features.attrs["as_of"])
                ranked = sorted(drivers, key=lambda row: (-row["logit_contribution"], row["feature"]))[:3]
                text = memo({**scored, "pillars": aggregate}, ranked, evidence.to_dict(orient="records"))
                target = config.path("memos") / arena / quarter / (values["entity_id"] + ".md")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
    result = pd.DataFrame(all_rows)
    if not result.empty:
        write_real_table(result, config.path("attributions") / arena / (quarter + ".parquet"))
    return result
