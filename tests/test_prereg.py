import json
from pathlib import Path

import pytest
import yaml

from prahari.config import Config
from prahari.eval.seal import freeze_benchmark, verify_benchmark_lock


def test_benchmark_lock_rejects_config_or_model_changes(tmp_path, config):
    # No records or reserved indices are written or read in this lock test.
    folder = tmp_path / "configs"
    folder.mkdir()
    base = config.base.copy()
    (folder / "base.yaml").write_text(yaml.safe_dump(base), encoding="utf-8")
    local = Config(folder / "base.yaml")
    local.path("models").mkdir(parents=True)
    local.path("benchmark_training_dir").mkdir(parents=True)
    artifact = local.path("models") / "fixture-model.bin"
    artifact.write_bytes(b"test-only model bytes, no data rows")
    local.path("benchmark_model_manifest").write_text(json.dumps([
        {"artifact": str(artifact.relative_to(tmp_path))}]), encoding="utf-8")
    freeze_benchmark(local)
    assert len(verify_benchmark_lock(local)) == 1
    artifact.write_bytes(b"changed model")
    with pytest.raises(ValueError, match="model changed"):
        verify_benchmark_lock(local)
    artifact.write_bytes(b"test-only model bytes, no data rows")
    (folder / "policy.yaml").write_text("changed: true", encoding="utf-8")
    with pytest.raises(ValueError, match="files changed"):
        verify_benchmark_lock(local)
