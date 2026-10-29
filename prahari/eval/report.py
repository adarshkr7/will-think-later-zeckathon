"""Generate report prose and tables exclusively from exported output artifacts."""

from __future__ import annotations

import json
import os

import pandas as pd

from prahari.config import Config
from prahari.data.output_store import OutputStore
from prahari.data.firewall import write_real_table
from prahari.data.uci import sha256_file


def markdown_table(table: pd.DataFrame, columns: list[str] | None = None) -> str:
    if table.empty:
        return "Not available in the current output bundle."
    data = table[columns] if columns else table
    def value(item):
        if pd.isna(item):
            return "unavailable"
        if isinstance(item, float):
            return f"{item:.5g}"
        return str(item).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(map(str, data.columns)) + " |", "| " + " | ".join("---" for _ in data.columns) + " |"]
    lines += ["| " + " | ".join(value(item) for item in row) + " |" for row in data.itertuples(index=False, name=None)]
    return "\n".join(lines)


def build_report(config: Config) -> None:
    output = OutputStore(config.path("app_manifest"))
    manifest = output.manifest
    report_path = config.path("final_report")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    trace = []
    def section(key: str, columns: list[str] | None = None, *, reference_only: bool = False) -> str:
        path = output.path(key)
        table = output.frame(key)
        if path.is_file():
            relative = os.path.relpath(path, report_path.parent).replace("\\", "/")
            trace.append({"section_source": key, "source_path": str(path.relative_to(config.root)).replace("\\", "/"),
                          "sha256": sha256_file(path), "rows": len(table), "is_synthetic": 0})
            return ("" if reference_only else markdown_table(table, columns) + "\n\n") + f"Source: [{key}]({relative})."
        return "Not run or not available. No numerical result is inferred."
    state = "Readiness report: production evaluation is incomplete" if manifest["mode"] == "readiness_only" else "Registered replay report"
    benchmark_columns = ["dataset", "representation", "variant", "horizon_quarters", "pr_auc", "pr_auc_ci_low", "pr_auc_ci_high", "base_rate", "brier", "evaluation_split"]
    lines = ["# PRAHARI", "", state, "",
             "## Problem and decision design", "",
             "PRAHARI reconstructs information available before each historical scoring cutoff. The primary model uses Polish-trained distress heads, a published market-risk layer and fixed soft-signal weights. Indian cases are evaluation outcomes, not primary training labels.", "",
             "## Current execution status", "", section("run_status"), "",
             "## Data and point-in-time design", "",
             "Source observations carry publication dates, conservative date-imputation flags and document references. Every feature source passes the as-of boundary. Later comparative statements retain the later source report's publication lag. Missing inputs retain explicit reasons.", "",
             section("collection_status"), "", section("panel_acceptance"), "",
             "### Original-vintage FX coverage", "", section("fx_coverage"), "",
             "FX comes from original weekly H.10 releases with actual publication dates. Revised current historical series are not substituted. Unreported source observations remain missing.", "",
             "The panel's current identity/classification catalog is distinct from historical matching-quarter availability. An empty event search does not establish a non-default peer or a negative governance signal.", "",
             "### Received peer-source audit", "",
             "Received candidate files are preserved separately and reviewed against original disclosures and historical exchange identities. Current identifiers, later financial years, rounded third-party observations and empty registry searches do not establish historical matching eligibility. Contrary original payment-status evidence is retained; the frozen selection rules are unchanged.", "",
             section("peer_intake_review", reference_only=True), "",
             "## Benchmark development", "",
             "The following are nested outer-fold or explicitly marked transfer development results. They are not untouched hold-out estimates. Bootstrap intervals condition on fitted predictions and do not cover model-selection uncertainty or correlated firm histories.", "",
             section("benchmark_development_metrics", benchmark_columns), "",
             "## Final benchmark", "", section("benchmark_final_metrics"), "",
             "## Indian panel evaluation", "", section("india_metrics"), "",
             "Scored production replay requires an accepted panel, independently sourced horizon priors and a matching pre-registration lock committed alone before replay. Unscored cases cannot be silently removed to flatter recall.", "",
             "## Policy and cost", "", section("app_policy"), "",
             "The operational review list uses the registered hard cap and deterministic tie handling. Additional-slot curves are counterfactual cost statistics and do not enlarge the operational list.", "",
             "For probability p, the expected cost of a miss is p times cost_fn; the expected cost of review is (1-p) times cost_fp. Equating them gives tau_star = cost_fp / (cost_fn + cost_fp). The policy table includes both equal expected costs at that threshold. Capacity is floor(alert_frac times the eligible population); a binding capacity limit further restricts the ranked list. These are policy calculations, not observed borrower losses.", "",
             section("cost_curve"), "", section("shadow_prices"), "", section("threshold_scan"), "",
             "## Attribution and evidence", "",
             "Native raw-margin TreeSHAP is rescaled to reconcile the nonlinear calibrated log-odds exactly. This path-proportional allocation is not presented as Shapley values of calibrated probability. CHS and overlay terms are linear. Single-driver probability removal effects overlap and are not additive or causal.", "",
             "Source deltas distinguish borrower documents from roll-forward and peer/universe-context effects, and must telescope between scored endpoints. A missing endpoint produces no invented evidence chain.", "",
             "## Ablation and detection", "", section("ablations"), "", section("detection_curve"), "",
             section("rating_lead_summary"), "", section("rating_lead_cases"), "",
             "Rating lead compares the first pre-event watch-list flag with the earliest sourced sub-investment-grade publication. The median uses paired observed endpoints; missing cases remain listed. Incomplete rating histories do not establish the first-ever downgrade. Calendar-quarter and day differences are both exported.", "",
             "## Placebo and anti-gaming", "", section("placebo"), "", section("anti_gaming"), "",
             "Counterfactual intervention inputs never replace source financials or enter the app as financial observations. A scenario that changes no active primary input is labelled ineffective and cannot establish robustness.", "",
             "## Monitoring and counterfactual policy experiments", "", section("drift"), "", section("hysteresis"), "", section("policy_scenarios"), "",
             "## Retrospective archetypes", "", section("archetypes"), "",
             "## Coverage parity", "", section("coverage_parity"), "",
             "## Case catalog", "", section("case_catalog", ["entity_id", "name", "sector", "event_date", "public_date", "needs_verification"]), "",
             "Case cards are exported for every reviewed case. Before registered evaluation, their status is not assessed rather than an invented hit or miss.", "",
             "## Limitations", "",
             "The data acceptance and source-coverage tables above are authoritative. Public data collection, complete peer survival evidence, historical classifications, share counts and regulatory-capital inputs may remain incomplete. Raw bhavcopy returns are unadjusted for corporate actions; cached price indices are not claimed to be total-return indices. Market-only background membership is not claimed to be a debt-ranked complete universe.", "",
             "The US CHS coefficients are not an Indian probability calibration. Annual-income proxies, universe-relative size and the plan's book-equity variant are explicit adaptations. Unknown priors do not fall back to panel prevalence. Financial-firm ranks are not called calibrated probabilities without a declared probability link.", "",
             "## Internal EWS workflow appendix", "", section("workflow"), "",
             "This is a design mapping to the cited historical framework. PRAHARI tiers and review targets are internal settings, not RBI-prescribed classifications or deadlines. A human institution makes any red-flag or fraud determination under its applicable approved process.", "",
             "## Amendments", "", output.text("amendments") or "No amendment log has been created.", "",
             "## Reproducibility", "",
             "Run `run_tests.ps1`, then `run_all.ps1 -Offline -Readiness` for a cached readiness build. Strict production execution preserves all data, registration and final-evaluation gates. Start the offline interface with `run_app.ps1`. The app reads only the exported output bundle.", ""]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    write_real_table(pd.DataFrame(trace), config.path("report_trace"))
    # Structural outline, with no manually copied performance claims.
    slides = ["# Pitch outline", "", "1. Credit desk time machine and the problem", "2. Published data and point-in-time boundary",
              "3. Development benchmark and untouched hold-out distinction", "4. Matched panel and coverage status",
              "5. Fixed primary model and separate financial track", "6. Hard review budget and cost curve",
              "7. Exact score reconciliation and evidence chain", "8. Every case, including misses and unavailable cases",
              "9. Ablation, placebo and limitations", "10. Reproducibility, registration and the independent sealed evaluation", "",
              "Populate numerical slides from the generated report and its output-source trace; do not type performance values by hand.", ""]
    config.path("slides_outline").write_text("\n".join(slides), encoding="utf-8")
