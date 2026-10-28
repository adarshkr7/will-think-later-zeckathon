"""Phase 2 collection-parity audits; outcome roles never enter primary training."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact


def coverage_parity(features: pd.DataFrame, cohorts: pd.DataFrame, fields: list[str], settings: dict) -> pd.DataFrame:
    """Fisher (1922), JRSS 85:87-94: two-sided exact 2x2 missingness test.

    A significant collection-induced difference restricts a field to Arena P.
    Unknown causes remain unresolved and are conservatively restricted too.
    Cohort rows are entity observations at the same collection/scoring cutoff.
    """
    if cohorts.entity_id.duplicated().any() or features.entity_id.duplicated().any():
        raise ValueError("Coverage audit requires one row per entity")
    if not cohorts.role.isin(["case", "peer"]).all():
        raise ValueError("Invalid cohort role")
    merged = cohorts.merge(features[["entity_id", *fields]], on="entity_id", how="left", validate="one_to_one")
    rows = []
    synthetic = int(cohorts.is_synthetic.eq(1).any() or features.is_synthetic.eq(1).any())
    for field in fields:
        case = merged.loc[merged.role.eq("case"), field]
        peer = merged.loc[merged.role.eq("peer"), field]
        counts = [[int(case.isna().sum()), int(case.notna().sum())],
                  [int(peer.isna().sum()), int(peer.notna().sum())]]
        cause = settings["collection_causes"].get(field, "unknown")
        if len(case) and len(peer):
            _, probability = fisher_exact(counts, alternative="two-sided")
            significant = probability < settings["fisher_alpha"]
            restricted = significant and cause != "not_collection_induced"
            reason = "collection_difference" if restricted else "no_significant_collection_difference"
            unresolved = int(significant and cause == "unknown")
        else:
            probability, restricted, unresolved, reason = np.nan, True, 1, "insufficient_cohorts"
        rows.append({"feature": field, "case_missing": counts[0][0], "case_present": counts[0][1],
                     "peer_missing": counts[1][0], "peer_present": counts[1][1],
                     "fisher_p": probability, "collection_cause": cause,
                     "arena_u_eligible": int(not restricted), "reason": reason,
                     "needs_verification": unresolved, "is_synthetic": synthetic})
    return pd.DataFrame(rows)
