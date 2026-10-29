"""Generate current collection counts from actual caches and verification flags."""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from prahari.config import Config
from prahari.data.bhavcopy import market_as_of
from prahari.data.financials import financials_as_of
from prahari.data.manual import read_manual
from prahari.data.firewall import assert_real, write_real_table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    now = pd.Timestamp.now(tz="UTC")
    market = market_as_of(config, now)
    fields = financials_as_of(config, now)
    documents = pd.read_csv(config.path("source_catalog"))
    cached = documents.status.eq("cached")
    events, peers = read_manual(config, "events"), read_manual(config, "peers")
    evidence = read_manual(config, "event_evidence")
    survival = read_manual(config, "peer_survival")
    fx = read_manual(config, "fx_rates")
    identities = read_manual(config, "security_crosswalk")
    statements = read_manual(config, "financial_evidence")
    shares = read_manual(config, "share_counts")
    holdings = read_manual(config, "shareholding")
    listings = read_manual(config, "listing_events")
    groups = read_manual(config, "groups")
    session_counts = read_manual(config, "trading_session_counts")
    calendar = read_manual(config, "trading_calendar")
    sessions = pd.read_csv(config.path("session_coverage")) if config.path("session_coverage").exists() else pd.DataFrame(columns=["status"])
    discovery = pd.read_csv(config.path("report_discovery_audit")) if config.path("report_discovery_audit").exists() else pd.DataFrame(columns=["status"])
    indexes = pd.read_csv(config.path("financial_index_coverage")) if config.path("financial_index_coverage").exists() else pd.DataFrame(columns=["status", "rows"])
    histories = pd.read_csv(config.path("financial_coverage")) if config.path("financial_coverage").exists() else pd.DataFrame(columns=["complete"])
    candidates = pd.read_csv(config.path("peer_discovery_candidates")) if config.path("peer_discovery_candidates").exists() else pd.DataFrame(columns=["entity_id", "symbol"])
    fx_coverage = pd.read_csv(config.path("fx_coverage")) if config.path("fx_coverage").exists() else pd.DataFrame(columns=["available"])
    rows = [("market_sessions", market.period_end.nunique(), 0),
            ("market_observations", len(market), 0),
            ("distinct_isins", market.entity_id.nunique(), 0),
            ("cached_source_pdfs", int(cached.sum()), 0),
            ("unavailable_source_pdfs", int((~cached).sum()), 1),
            ("verified_financial_fields", len(fields), 0),
            ("financial_entities", fields.entity_id.nunique(), 0),
            ("financial_evidence_rows", len(statements), 0),
            ("verified_financial_evidence_rows", int(statements.needs_verification.eq(0).sum()), 0),
            ("cached_original_report_candidates", int(discovery.loc[discovery.status.eq("cached_original_candidate"), "source_url"].nunique()) if "source_url" in discovery else 0, 1),
            ("cached_financial_index_windows", int(indexes.status.eq("cached_index").sum()), 0),
            ("financial_index_records", int(indexes.loc[indexes.status.eq("cached_index"), "rows"].sum()), 0),
            ("verified_identity_mappings", int(identities.needs_verification.eq(0).sum()), 0),
            ("verified_quarterly_share_counts", int(shares.needs_verification.eq(0).sum()), 0),
            ("verified_quarterly_shareholding", int(holdings.needs_verification.eq(0).sum()), 0),
            ("verified_first_listing_certificates", int(listings.needs_verification.eq(0).sum()), 0),
            ("sourced_group_memberships", int(groups.needs_verification.eq(0).sum()), 0),
            ("complete_group_roster_memberships", int((groups.needs_verification.eq(0) & groups.membership_complete.eq(1)).sum()), 0),
            ("published_session_count_claims", int(session_counts.needs_verification.eq(0).sum()), 0),
            ("certified_session_census_periods", int(sessions.status.eq("complete_census").sum()), 0),
            ("sourced_exchange_calendar_rows", int(calendar.needs_verification.eq(0).sum()), 0),
            ("complete_core_financial_histories", int(histories.complete.eq(1).sum()), 0),
            ("unselected_research_symbols", candidates.symbol.nunique(), 1),
            ("unselected_research_security_ids", candidates.entity_id.nunique(), 1),
            ("unselected_research_pairs", len(candidates), 1),
            ("verified_survival_candidates", survival.loc[survival.needs_verification.eq(0), "entity_id"].nunique(), 0),
            ("verified_survival_pairs", int(survival.needs_verification.eq(0).sum()), 0),
            ("verified_panel_events", events.loc[events.needs_verification.eq(0), "entity_id"].nunique(), 0),
            ("verified_case_isins", int((events.needs_verification.eq(0) & events["isin"].astype(str).str.fullmatch(r"IN[A-Z0-9]{10}")).sum()), 0),
            ("verified_case_classifications", int((events.needs_verification.eq(0) & events.sector.notna() & events.is_financial.isin([0, 1])).sum()), 0),
            ("verified_event_components", int(evidence.needs_verification.eq(0).sum()), 0),
            ("verified_fx_observations", int(fx.needs_verification.eq(0).sum()), 0),
            ("quarters_with_verified_fx", int(fx_coverage.available.eq(1).sum()), 0),
            ("verified_matched_peers", peers.loc[peers.needs_verification.eq(0), "entity_id"].nunique(), 1)]
    table = pd.DataFrame([{"item": name, "observed": value, "needs_verification": pending, "is_synthetic": 0}
                          for name, value, pending in rows])
    if config.path("peer_intake_review").exists():
        intake = pd.read_csv(config.path("peer_intake_review"))
        assert_real(intake)
        counts = {"received_peer_claims": len(intake),
                  "received_peer_files": intake.received_file.nunique(),
                  "received_peer_claims_approved_for_model": int(intake.approved_for_model.eq(1).sum())}
        table = pd.concat([table, pd.DataFrame([{"item": name, "observed": value,
            "needs_verification": 0, "is_synthetic": 0} for name, value in counts.items()])], ignore_index=True)
    write_real_table(table, config.path("collection_status"))


if __name__ == "__main__":
    main()
