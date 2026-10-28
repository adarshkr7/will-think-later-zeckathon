"""Initialize panel templates or validate human inputs; empty panels fail acceptance."""

import argparse
import logging
import sys
import pandas as pd
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.data.firewall import write_real_table
from prahari.data.quality import accounting_from_fields, initialize_templates, validate_manual
from prahari.data.manual import read_manual
from prahari.data.financials import financials_as_of
from prahari.eval.panel_quality import audit_coverage, audit_market, audit_financial_histories, panel_acceptance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--init-templates", action="store_true")
    parser.add_argument("--as-of", help="Publication cutoff for collection-parity audit")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    if args.init_templates:
        initialize_templates(config)
        return
    summary = validate_manual(config)
    write_real_table(summary, config.path("manual_validation"))
    settings = config.section("manual_config")["validation"]
    accounting = accounting_from_fields(financials_as_of(config, pd.Timestamp.now(tz="UTC")), settings["accounting_tolerance"])
    write_real_table(accounting, config.path("accounting_coverage"))
    market = audit_market(config)
    write_real_table(market, config.path("market_coverage"))
    financials = audit_financial_histories(config)
    write_real_table(financials, config.path("financial_coverage"))
    checks = panel_acceptance(read_manual(config, "events"), read_manual(config, "peers"), market,
                              accounting, config.section("india_config")["panel"], financials)
    write_real_table(checks, config.path("panel_acceptance"))
    if args.as_of:
        write_real_table(audit_coverage(config, args.as_of), config.path("coverage_parity"))
    if not checks.passed.eq(1).all():
        raise SystemExit("Panel acceptance incomplete; inspect outputs/panel_acceptance.csv and DATA_REQUESTS.md")
    logging.info("Panel schema, cohort, accounting and market-coverage checks passed")


if __name__ == "__main__":
    main()
