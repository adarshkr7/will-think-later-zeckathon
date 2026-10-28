from pathlib import Path

import pandas as pd
import pytest

from prahari.data.firewall import assert_real, write_real_table


def test_fixture_flags(benchmark_fixture, observations):
    assert benchmark_fixture.is_synthetic.eq(1).all()
    assert observations.is_synthetic.eq(1).all()


def test_all_csv_fixtures_are_explicitly_synthetic():
    for path in Path(__file__).parent.joinpath("fixtures").glob("*.csv"):
        table = pd.read_csv(path)
        assert "is_synthetic" in table, path.name
        assert table.is_synthetic.eq(1).all(), path.name


def test_synthetic_write_rejected_before_file_creation(benchmark_fixture, tmp_path):
    path = tmp_path / "forbidden.parquet"
    with pytest.raises(ValueError, match="Synthetic"):
        write_real_table(benchmark_fixture, path)
    assert not path.exists()


def test_missing_provenance_rejected(benchmark_fixture):
    with pytest.raises(ValueError, match="Missing is_synthetic"):
        assert_real(benchmark_fixture.drop(columns="is_synthetic"))


def test_production_tables_are_real_without_reading_reserved_partitions(config):
    # Never recurse into benchmark_seals or manual/sealed, even in integrity tests.
    files = list(config.path("benchmark_training_dir").glob("*.parquet"))
    processed = config.path("processed")
    files += list(processed.glob("*.parquet")) + list(processed.glob("*.csv"))
    # Explicit unsealed locations: never recurse through protected benchmark
    # partitions or manual/sealed while checking new nested feature caches.
    for key in ("feature_cache", "universe_cache"):
        files += list(config.path(key).glob("*/*.parquet"))
    if config.path("outputs").exists():
        files += list(config.path("outputs").rglob("*.csv")) + list(config.path("outputs").rglob("*.parquet"))
    for path in files:
        assert "holdout" not in path.name.lower(), "Never inspect a reserved partition in general tests"
        table = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
        assert_real(table)
