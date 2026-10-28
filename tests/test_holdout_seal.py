import json
from pathlib import Path

import pytest

from prahari.eval.seal import claim_once, code_fingerprint


def test_once_only_claim_even_after_failed_final_run(tmp_path):
    path = tmp_path / "access.json"
    claim_once(path)
    assert json.loads(path.read_text())["state"] == "claimed"
    with pytest.raises(RuntimeError, match="second opening"):
        claim_once(path)


def test_fingerprint_does_not_read_sealed_files(config, monkeypatch):
    original = Path.read_bytes
    def guarded(path):
        assert "sealed" not in path.parts and "benchmark_seals" not in path.parts
        assert "holdout" not in path.name.lower()
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", guarded)
    fingerprint = code_fingerprint(config)
    assert "configs/policy.yaml" in fingerprint
    assert "prahari/models/benchmark.py" in fingerprint
