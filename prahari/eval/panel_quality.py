"""Phase 2 acceptance and collection coverage, separate from primary training."""

from __future__ import annotations

import math

import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.financials import financial_table
from prahari.data.manual import read_manual
from prahari.eval.coverage import coverage_parity


def panel_acceptance(events: pd.DataFrame, peers: pd.DataFrame, market: pd.DataFrame,
                     accounting: pd.DataFrame, settings: dict, financials: pd.DataFrame | None = None) -> pd.DataFrame:
    """No event/peer duplication or incomplete market checks can pass the gate."""
    events = events.loc[events.needs_verification.eq(0)]
    peers = peers.loc[peers.needs_verification.eq(0)]
    case_ids, peer_ids = set(events.entity_id), set(peers.entity_id)
    adequate_matches = all(peers.loc[peers.matched_to.eq(entity)].entity_id.nunique() >= settings["peers_per_case"]
                           for entity in case_ids) and bool(case_ids)
    stressed = peers.drop_duplicates("entity_id").is_stressed_survivor.eq(1).sum()
    market_ok = (not market.empty and {"entity_id", "complete"}.issubset(market)
                 and (case_ids | peer_ids).issubset(set(market.loc[market.complete.eq(1), "entity_id"])))
    identity_ok = not accounting.empty and accounting.identity_status.eq("pass").all()
    financial_ok = False
    if financials is not None and not financials.empty:
        verified = financials.loc[financials.needs_verification.eq(0) & financials.basis.eq("standalone")]
        years = verified.groupby("entity_id").fy_end.nunique()
        financial_ok = bool(case_ids) and all(years.get(entity, 0) >= settings["minimum_financial_years"]
                                             for entity in case_ids | peer_ids)
    checks = [("verified_events", len(case_ids), settings["minimum_cases"], len(case_ids) >= settings["minimum_cases"]),
              ("unique_verified_peers", len(peer_ids), settings["minimum_unique_peers"], len(peer_ids) >= settings["minimum_unique_peers"]),
              ("disjoint_cases_peers", len(case_ids & peer_ids), 0, not case_ids.intersection(peer_ids)),
              ("peers_per_case", int(adequate_matches), 1, adequate_matches),
              ("stressed_survivors", int(stressed), math.ceil(len(peer_ids) * settings["stressed_fraction"]),
               bool(peer_ids) and stressed >= math.ceil(len(peer_ids) * settings["stressed_fraction"])),
              ("panel_market_coverage", int(market_ok), 1, market_ok),
              ("financial_year_coverage", int(financial_ok), 1, financial_ok),
              ("accounting_identities", int(identity_ok), 1, identity_ok)]
    return pd.DataFrame([{"check": name, "observed": value, "required": required, "passed": int(passed),
                          "is_synthetic": int(events.is_synthetic.eq(1).any() or peers.is_synthetic.eq(1).any())}
                         for name, value, required, passed in checks])


def audit_coverage(config: Config, t: str) -> pd.DataFrame:
    events, peers = read_manual(config, "events"), read_manual(config, "peers")
    events, peers = events.loc[events.needs_verification.eq(0)], peers.loc[peers.needs_verification.eq(0)]
    cohorts = pd.concat([events[["entity_id", "is_synthetic"]].assign(role="case"),
                         peers[["entity_id", "is_synthetic"]].drop_duplicates("entity_id").assign(role="peer")])
    snapshot = as_of(financial_table(config), t)
    snapshot = snapshot.loc[snapshot.basis.eq("standalone")].sort_values("period_end")
    snapshot = snapshot.drop_duplicates(["entity_id", "field"], keep="last")
    fields = config.section("manual_config")["tables"]["annual_financials"]["numeric"]
    if snapshot.empty:
        wide = pd.DataFrame(columns=["entity_id", *fields, "is_synthetic"])
    else:
        wide = snapshot.pivot(index="entity_id", columns="field", values="value").reset_index()
        wide["is_synthetic"] = 0
        for field in fields:
            if field not in wide:
                wide[field] = float("nan")
    return coverage_parity(wide, cohorts, fields, config.section("india_config")["coverage"])
