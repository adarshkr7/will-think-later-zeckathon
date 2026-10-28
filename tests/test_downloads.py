import requests
import pytest

from prahari.data.downloads import CachedDownloader, SourceBlocked


def test_repeated_exchange_blocks_stop_at_configured_limit(config, monkeypatch):
    downloader = CachedDownloader(config)
    calls, failures = [], []
    def blocked(url, **kwargs):
        calls.append(url)
        response = requests.Response()
        response.status_code = 403
        response.url = url
        return response
    monkeypatch.setattr(downloader.session, "get", blocked)
    monkeypatch.setattr(downloader, "_record_failure", lambda *args: failures.append(args))
    monkeypatch.setattr("prahari.data.downloads.time.sleep", lambda seconds: None)
    with pytest.raises(SourceBlocked):
        downloader.fetch("fixtureblocked", "https://fixture.invalid/report", "report.zip")
    assert len(calls) == config.section("india_config")["network"]["block_attempts"]
    assert len(failures) == 1
    downloader.close()


def test_offline_access_never_attempts_network(config, monkeypatch):
    downloader = CachedDownloader(config)
    monkeypatch.setattr(downloader.session, "get", lambda *args, **kwargs: pytest.fail("Unexpected network access"))
    with pytest.raises(FileNotFoundError):
        downloader.fetch("fixturemissing", "https://fixture.invalid/file", "missing.zip", offline=True)
    downloader.close()


def test_cache_names_reject_traversal(config):
    downloader = CachedDownloader(config)
    with pytest.raises(ValueError, match="traversal"):
        downloader.fetch("nse", "https://fixture.invalid/file", "../outside.zip")
    downloader.close()
