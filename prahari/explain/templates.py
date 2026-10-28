"""The sole source of memo/explanation prose. No generated-language service."""

from __future__ import annotations

import math
import pandas as pd
from collections.abc import Mapping


TEMPLATES = {
    "roa": ("Profitability relative to assets is {value}.", "Reconcile earnings with operating cash flow."),
    "tl_ta": ("Liabilities relative to assets are {value}.", "Review the debt maturity schedule and covenant headroom."),
    "wc_ta": ("Working capital relative to assets is {value}.", "Check receivable ageing and near-term payments."),
    "current_ratio": ("Current asset coverage of current liabilities is {value}.", "Verify liquidity using realizable assets."),
    "quick_ratio": ("Liquid current asset coverage is {value}.", "Test liquidity without inventory liquidation."),
    "re_ta": ("Retained earnings relative to assets are {value}.", "Review accumulated losses and capital buffers."),
    "ebit_ta": ("Operating earnings relative to assets are {value}.", "Separate recurring operating income from exceptional items."),
    "equity_tl": ("Book equity relative to liabilities is {value}.", "Review loss absorption capacity."),
    "equity_ta": ("The reported equity buffer is {value} of assets.", "Check capital erosion and contingent obligations."),
    "sales_ta": ("Asset turnover is {value}.", "Verify the operating assets supporting reported sales."),
    "sales_growth": ("The current-to-prior sales ratio is {value}.", "Check growth against collections and contract evidence."),
    "gp_dep_tl": ("Gross profit plus depreciation relative to liabilities is {value}.", "Review coverage using recurring cash earnings."),
    "cl_ta": ("Current liabilities relative to assets are {value}.", "Review refinancing concentration."),
    "cash_ta": ("Cash and short-term investments relative to assets are {value}.", "Confirm balances and encumbrances."),
    "nimtaavg": ("Weighted earnings relative to market-valued assets are {value}.", "Review the earnings trajectory and cash realization."),
    "tlmta": ("Liabilities relative to market-valued assets are {value}.", "Stress-test refinancing against market equity erosion."),
    "cashmta": ("Liquid resources relative to market-valued assets are {value}.", "Verify accessible liquidity and restrictions."),
    "exretavg": ("Weighted excess price return is {value}.", "Investigate sustained underperformance and funding access."),
    "sigma": ("Observed annualized equity volatility is {value}.", "Review abrupt market dislocations and corporate actions."),
    "relsize": ("Log market equity relative to the observed universe is {value}.", "Assess market access and concentration."),
    "mb": ("The market-to-book equity input is {value}.", "Inspect book-equity quality and the configured floor."),
    "price": ("The capped log-price input is {value}.", "Verify price units, cap assumptions and corporate actions."),
    "auditor_exit_8q": ("The observed auditor-exit signal is {value}.", "Obtain the resignation letter and unresolved audit issues."),
    "rating_watch_neg_or_inc": ("The rating watch or non-cooperation signal is {value}.", "Read the contemporaneous agency rationale."),
    "rating_notch_delta_4q": ("The observed rating deterioration is {value} notches.", "Review instrument-specific repayment risks."),
    "pledge_jump": ("The registered pledge-jump signal is {value}.", "Check pledge covenants and invocation risk."),
    "pledge_pct": ("Promoter shares pledged as a percentage of promoter holdings are {value}.", "Verify disclosure coverage and encumbrances."),
    "pledge_delta_4q": ("The observed pledge change is {value} percentage points.", "Review changes in promoter funding pressure."),
    "delayed_filing_4q": ("The observed delayed-filing signal is {value}.", "Obtain the filing explanation and pending statements."),
    "audit_default_or_going_concern": ("The sourced audit default or going-concern signal is {value}.", "Escalate the audit evidence and cash-flow assessment."),
    "nbfc_score": ("The financial-firm scorecard rank is {value}.", "Review ALM, capital adequacy, asset quality and short-term funding."),
    "cash_conversion_gap": ("The earnings-to-operating-cash gap is {value} of assets.", "Trace non-cash earnings and collections."),
    "consolidated_standalone_debt": ("The reported consolidated-to-standalone debt ratio is {value}.", "Review guarantees, SPVs and consolidation boundaries."),
    "cwip_ta": ("Capital work in progress relative to assets is {value}.", "Review project completion and capitalization policies."),
    "group_stress": ("The sourced group-stress signal is {value}.", "Review dated ownership links and guarantees."),
}


def display(value: object) -> str:
    if value is None or value is pd.NA or value is pd.NaT:
        return "unknown"
    if isinstance(value, (int, float)):
        return f"{value:.4g}" if math.isfinite(value) else "unknown"
    return str(value)


def driver_text(name: str, values: Mapping) -> str:
    missing = name.endswith("__missing")
    canonical = name.removesuffix("__missing")
    if canonical not in TEMPLATES:
        raise ValueError("No deterministic explanation template for " + name)
    if missing:
        return f"The {canonical} input is missing; the frozen benchmark missing-value treatment contributed to the score. Obtain the original disclosure."
    concern, action = TEMPLATES[canonical]
    context = {key: display(value) for key, value in values.items()}
    context.setdefault("value", "unknown")
    return concern.format_map(context) + " " + action


def memo(header: Mapping, drivers: list[Mapping], evidence: list[Mapping]) -> str:
    label = header.get("name")
    if pd.isna(label):
        label = header.get("symbols")
    if pd.isna(label):
        label = header["entity_id"]
    lines = [f"# Credit review: {label}",
             f"Scoring date: {display(header.get('scoring_date'))}",
             f"Rank: {display(header.get('rank'))}; tier: {display(header.get('tier'))}",
             f"Model probability (4Q): {display(header.get('pd_4q'))}; (8Q): {display(header.get('pd_8q'))}",
             f"Observed hard trigger: {display(header.get('hard_trigger'))}"]
    for driver in drivers:
        lines.append("- " + driver_text(driver["feature"], driver) + f" Removal effect: {display(driver.get('pd_points'))} percentage points.")
    lines.append("Single-driver probability removal effects overlap and do not add up to total probability. They describe model sensitivity, not causation.")
    for name, value in header.get("pillars", {}).items():
        lines.append(f"- Pillar {name}: {display(value)} log-odds contribution.")
    lines.append("\nDated evidence:")
    for item in evidence:
        lines.append(f"- {display(item.get('public_date'))}: {display(item.get('source_url') or item.get('source_doc'))}")
    if not drivers:
        lines.append("No scored explanation is available because required evidence or registration is incomplete.")
    return "\n".join(lines) + "\n"


def case_unavailable(record: Mapping, reason: str) -> str:
    return (f"# {record.get('name') or record['entity_id']}\n\n"
            f"Verified event: {display(record.get('event_date'))}.\n\n"
            f"Evaluation status: not assessed. {reason}\n\n"
            "No hit, miss or lead-time claim is made before a registered scored replay.\n")


def case_card(record: Mapping, observations: list[Mapping], path: list[Mapping]) -> str:
    lines = [f"# {record.get('name') or record['entity_id']}", "",
             f"Verified qualifying event: {display(record.get('event_date'))}.", "",
             "## Strict single-quarter evaluation", ""]
    for row in observations:
        outcome = "hit" if row["hit"] == 1 else "miss"
        lines.append(f"- {display(row['lead_quarters'])}Q lead: {outcome}; status {display(row['status'])}; required cutoff {display(row['required_scoring_date'])}.")
    lines += ["", "## Stored probability and rank path", "", "| Cutoff | PD 4Q | Rank | Budget | Tier |", "|---|---|---|---|---|"]
    for row in path:
        lines.append("| " + " | ".join(display(row.get(name)) for name in ("scoring_date", "pd_4q", "rank", "review_cap", "tier")) + " |")
    lines += ["", "Incomplete score coverage is retained in the evaluation denominator. No causal explanation is inferred from a missed or unavailable score.", ""]
    return "\n".join(lines)
