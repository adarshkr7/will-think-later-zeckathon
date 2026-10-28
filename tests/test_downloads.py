import requests
import pytest

from prahari.data.downloads import CachedDownloader, SourceBlocked, SourceUnavailable


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


def test_official_404_is_cached_but_not_claimed_as_holiday(config, tmp_path, monkeypatch):
    config.base["paths"]["raw"] = str(tmp_path / "raw")
    downloader = CachedDownloader(config)
    calls = []
    def absent(url, **kwargs):
        calls.append(url)
        response = requests.Response()
        response.status_code, response.url = 404, url
        return response
    monkeypatch.setattr(downloader.session, "get", absent)
    with pytest.raises(SourceUnavailable):
        downloader.fetch("fixture404", "https://fixture.invalid/missing", "missing.zip")
    with pytest.raises(SourceUnavailable):
        downloader.fetch("fixture404", "https://fixture.invalid/missing", "missing.zip", offline=True)
    assert len(calls) == 1
    assert not (tmp_path / "raw" / "fixture404" / "missing.zip").exists()
    downloader.close()
