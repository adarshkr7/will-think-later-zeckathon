import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from prahari.models.development_cache import verify_requirements

DATA = json.loads((Path(__file__).parent / "fixtures" / "benchmark_dependencies.json").read_text())


@pytest.mark.parametrize("name", ["original", "added"])
def test_cached_environment_allows_same_pins_and_added_packages(tmp_path, monkeypatch, name):
    original = DATA["original"].encode()
    (tmp_path / "requirements.txt").write_bytes(DATA[name].encode())
    monkeypatch.setattr("prahari.models.development_cache.subprocess.check_output",
                        lambda args, **kwargs: b"fixture_commit\n" if args[1] == "log" else original)
    verify_requirements(SimpleNamespace(root=tmp_path), "requirements.txt", hashlib.sha256(original).hexdigest())


def test_cached_environment_rejects_changed_dependency(tmp_path, monkeypatch):
    original = DATA["original"].encode()
    (tmp_path / "requirements.txt").write_bytes(DATA["changed"].encode())
    monkeypatch.setattr("prahari.models.development_cache.subprocess.check_output",
                        lambda args, **kwargs: b"fixture_commit\n" if args[1] == "log" else original)
    with pytest.raises(ValueError, match="dependency pin changed"):
        verify_requirements(SimpleNamespace(root=tmp_path), "requirements.txt", hashlib.sha256(original).hexdigest())


def test_cached_environment_requires_verifiable_history(tmp_path, monkeypatch):
    original = DATA["original"].encode()
    (tmp_path / "requirements.txt").write_bytes(DATA["added"].encode())
    monkeypatch.setattr("prahari.models.development_cache.subprocess.check_output", lambda *args, **kwargs: b"")
    with pytest.raises(ValueError, match="Cannot verify"):
        verify_requirements(SimpleNamespace(root=tmp_path), "requirements.txt", hashlib.sha256(original).hexdigest())
