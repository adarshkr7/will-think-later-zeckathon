import json

import pytest

from conftest import FIXTURES
from prahari.data.feature_lineage import verify_feature_receipt, write_feature_receipt


def test_source_updates_and_artifact_edits_invalidate_feature_cache(config, tmp_path):
    fixture = json.loads((FIXTURES / "feature_lineage.json").read_text())
    artifact = tmp_path / "cache.parquet"
    artifact.write_text(fixture["artifact_bytes"], encoding="utf-8")
    write_feature_receipt(config, artifact, fixture["inputs"])
    verify_feature_receipt(config, artifact, fixture["inputs"])
    with pytest.raises(RuntimeError, match="sources changed"):
        verify_feature_receipt(config, artifact, fixture["changed_inputs"])
    artifact.write_text(fixture["changed_artifact_bytes"], encoding="utf-8")
    with pytest.raises(RuntimeError, match="artifact changed"):
        verify_feature_receipt(config, artifact, fixture["inputs"])


def test_legacy_feature_caches_cannot_be_registered_without_source_receipts(config, tmp_path):
    fixture = json.loads((FIXTURES / "feature_lineage.json").read_text())
    artifact = tmp_path / "legacy.parquet"
    artifact.write_text(fixture["artifact_bytes"], encoding="utf-8")
    with pytest.raises(RuntimeError, match="receipt missing"):
        verify_feature_receipt(config, artifact, fixture["inputs"])
