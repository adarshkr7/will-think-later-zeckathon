from conftest import FIXTURES
from prahari.data.report_discovery import annual_links


def test_report_discovery_uses_explicit_labels_not_filenames(config):
    links = annual_links((FIXTURES / "document_links.html").read_bytes(), "https://fixture.test/issuer/", config.section("report_discovery_config")["annual_label_pattern"])
    assert links == [(2015, "https://fixture.test/issuer/report_a.pdf", 1), (2016, "https://fixture.test/issuer/report_b.pdf", 1)]
