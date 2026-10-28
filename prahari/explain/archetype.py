"""Nearest explanation archetype, excluding the borrower and its case group."""

import numpy as np
import pandas as pd


def nearest_archetype(entity_id: str, case_group: str, vector: np.ndarray, library: pd.DataFrame,
                      feature_columns: list[str]) -> dict:
    eligible = library.loc[library.entity_id.ne(entity_id) & library.case_group.ne(case_group)].copy()
    values = np.asarray(vector, dtype=float)
    norm = np.linalg.norm(values)
    if eligible.empty or not np.isfinite(values).all() or norm == 0:
        return {"archetype": None, "distance": np.nan, "reason": "no_eligible_nonzero_archetype"}
    matrix = eligible[feature_columns].to_numpy(dtype=float)
    lengths = np.linalg.norm(matrix, axis=1)
    valid = np.isfinite(matrix).all(axis=1) & (lengths > 0)
    if not valid.any():
        return {"archetype": None, "distance": np.nan, "reason": "no_eligible_nonzero_archetype"}
    distances = np.linalg.norm(matrix[valid] / lengths[valid, None] - values / norm, axis=1)
    eligible = eligible.loc[valid].assign(distance=distances).sort_values(["distance", "entity_id"], kind="stable")
    return {"archetype": eligible.iloc[0].entity_id, "distance": eligible.iloc[0].distance, "reason": ""}
