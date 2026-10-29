import json

import pandas as pd

from conftest import FIXTURES
from prahari.data.report_discovery import annual_links, candidate_report_window


def test_report_discovery_uses_explicit_labels_not_filenames(config):
    links = annual_links((FIXTURES / "document_links.html").read_bytes(), "https://fixture.test/issuer/", config.section("report_discovery_config")["annual_label_pattern"])
    assert links == [(2015, "https://fixture.test/issuer/report_a.pdf", 1), (2016, "https://fixture.test/issuer/report_b.pdf", 1)]


def test_survival_acquisition_reaches_the_report_covering_the_endpoint(config):
    fixture = json.loads((FIXTURES / "report_windows.json").read_text())
    for case in fixture["cases"]:
        window = candidate_report_window(pd.Timestamp(case["event_date"]), config.section("india_config")["panel"],
                                         config.section("report_discovery_config")["report_label_fiscal_year_end"])
        assert window == (case["first_year"], case["last_year"])
