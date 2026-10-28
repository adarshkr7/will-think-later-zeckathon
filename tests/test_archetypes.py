import numpy as np
import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.explain.archetype import nearest_archetype


def test_archetype_excludes_self_and_own_case_component():
    library = pd.read_csv(FIXTURES / "archetypes.csv")
    result = nearest_archetype("FIX_A", "GROUP_A", np.array([1., 0.]), library, ["liquidity", "solvency"])
    assert result["archetype"] == "FIX_C"
    assert result["distance"] == pytest.approx(np.sqrt(2))
    assert nearest_archetype("FIX_A", "GROUP_A", np.array([0., 0.]), library, ["liquidity", "solvency"])["archetype"] is None
