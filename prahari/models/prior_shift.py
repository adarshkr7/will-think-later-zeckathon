"""Fixed prior-odds adjustment; never estimates Indian priors from case labels."""

from __future__ import annotations

import numpy as np


def prior_shift(p: np.ndarray | float, pi_old: float, pi_new: float) -> np.ndarray:
    """Saerens, Latinne & Decaestecker (2002), Neural Computation 14:21-41.

    Adjust binary posterior odds by new prior odds / training prior odds.
    Valid only under label shift; this assumption must be reported explicitly.
    """
    values = np.asarray(p, dtype=float)
    if not 0 < pi_old < 1 or not 0 < pi_new < 1:
        raise ValueError("Both priors must be strictly between zero and one")
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("Probabilities must be finite and in [0, 1]")
    numerator = values * pi_new / pi_old
    denominator = numerator + (1 - values) * (1 - pi_new) / (1 - pi_old)
    return numerator / denominator
