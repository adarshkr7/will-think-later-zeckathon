import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.explain.provenance import telescoping_trace


def test_provenance_telescopes_with_time_and_peer_context():
    items = pd.read_csv(FIXTURES / "provenance.csv")
    result = telescoping_trace(items, "2019-10-01", "2019-12-31", .20, .33,
                              lambda prefix: .21 + prefix.value.sum(), tolerance=.000001)
    assert result.delta_pd.sum() == pytest.approx(.13)
    assert result.iloc[0].delta_pd == pytest.approx(.01)
    assert result.iloc[-1].delta_pd == pytest.approx(.04)
    assert result.iloc[-1].kind == "peer_and_universe_context"
    assert result.is_synthetic.eq(1).all()
    with pytest.raises(ValueError, match="outside"):
        telescoping_trace(items, "2019-10-03", "2019-12-31", .2, .3, lambda prefix: .2, tolerance=.000001)
