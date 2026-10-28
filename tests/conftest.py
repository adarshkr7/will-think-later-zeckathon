from pathlib import Path

import pandas as pd
import pytest

from prahari.config import Config

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def observations():
    return pd.read_csv(FIXTURES / "asof.csv")


@pytest.fixture
def benchmark_fixture():
    return pd.read_csv(FIXTURES / "benchmark.csv").set_index("row_id")
