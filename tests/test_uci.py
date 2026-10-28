import pytest

from prahari.data.benchmark_store import prepare_training
from prahari.data.uci import download
from prahari.features.harmonize import harmonize


def test_missing_offline_cache_never_downloads(config, tmp_path, monkeypatch):
    monkeypatch.setitem(config.base["paths"], "raw", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="Offline cache"):
        download(config, "polish", offline=True)


def test_cached_training_and_documented_mappings_without_opening_holdouts(config, monkeypatch):
    # Development accessor must never touch any reserved file, even on reruns.
    original = type(config.file).read_bytes
    def guarded(path):
        assert "benchmark_seals" not in path.parts
        assert "holdout" not in path.name.lower()
        return original(path)
    monkeypatch.setattr(type(config.file), "read_bytes", guarded)
    for name, spec in config.section("benchmark_config")["datasets"].items():
        if not (config.path("benchmark_training_dir") / f"{name}.parquet").exists():
            pytest.skip("Official benchmark cache not prepared")
        table = prepare_training(config, name, offline=True)
        assert 0 < len(table) < spec["rows"]
        assert table.is_synthetic.eq(0).all()
        features = harmonize(table, spec["source"], config.section("harmonized_map"), shared_only=True)
        assert len(features.columns) == 10


def test_harmonization_rejects_unverified_column(benchmark_fixture, config):
    with pytest.raises(ValueError, match="Unverified or missing"):
        harmonize(benchmark_fixture, "polish", config.section("harmonized_map"), shared_only=True)
