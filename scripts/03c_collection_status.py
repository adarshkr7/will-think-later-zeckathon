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
from prahari.data.firewall import write_real_table


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
    fx = read_manual(config, "fx_rates")
    identities = read_manual(config, "security_crosswalk")
    statements = read_manual(config, "financial_evidence")
    shares = read_manual(config, "share_counts")
    holdings = read_manual(config, "shareholding")
    discovery = pd.read_csv(config.path("report_discovery_audit")) if config.path("report_discovery_audit").exists() else pd.DataFrame(columns=["status"])
    indexes = pd.read_csv(config.path("financial_index_coverage")) if config.path("financial_index_coverage").exists() else pd.DataFrame(columns=["status", "rows"])
    histories = pd.read_csv(config.path("financial_coverage")) if config.path("financial_coverage").exists() else pd.DataFrame(columns=["complete"])
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
            ("cached_original_report_candidates", int(discovery.status.eq("cached_original_candidate").sum()), 1),
            ("cached_financial_index_windows", int(indexes.status.eq("cached_index").sum()), 0),
            ("financial_index_records", int(indexes.loc[indexes.status.eq("cached_index"), "rows"].sum()), 0),
            ("verified_identity_mappings", int(identities.needs_verification.eq(0).sum()), 0),
            ("verified_quarterly_share_counts", int(shares.needs_verification.eq(0).sum()), 0),
            ("verified_quarterly_shareholding", int(holdings.needs_verification.eq(0).sum()), 0),
            ("complete_core_financial_histories", int(histories.complete.eq(1).sum()), 0),
            ("verified_panel_events", events.loc[events.needs_verification.eq(0), "entity_id"].nunique(), 0),
            ("verified_case_isins", int((events.needs_verification.eq(0) & events["isin"].astype(str).str.fullmatch(r"IN[A-Z0-9]{10}")).sum()), 0),
            ("verified_case_classifications", int((events.needs_verification.eq(0) & events.sector.notna() & events.is_financial.isin([0, 1])).sum()), 0),
            ("verified_event_components", int(evidence.needs_verification.eq(0).sum()), 0),
            ("verified_fx_observations", int(fx.needs_verification.eq(0).sum()), 0),
            ("quarters_with_verified_fx", int(fx_coverage.available.eq(1).sum()), 0),
            ("verified_matched_peers", peers.loc[peers.needs_verification.eq(0), "entity_id"].nunique(), 1)]
    table = pd.DataFrame([{"item": name, "observed": value, "needs_verification": pending, "is_synthetic": 0}
                          for name, value, pending in rows])
    write_real_table(table, config.path("collection_status"))


if __name__ == "__main__":
    main()
