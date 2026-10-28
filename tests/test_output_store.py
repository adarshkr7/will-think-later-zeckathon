import json

import pytest

from prahari.data.output_store import OutputStore


def test_app_bundle_rejects_traversal_before_reading_files(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"files": {"bad": "../outside.csv", "memos": "memos"}}), encoding="utf-8")
    store = OutputStore(manifest)
    assert store.frame("optional_not_yet_exported").empty
    assert store.text("optional_not_yet_exported") == ""
    with pytest.raises(ValueError, match="escapes"):
        store.frame("bad")
    with pytest.raises(ValueError, match="escapes"):
        store.text("memos", "..", "..", "outside.md")
