"""Retrospective explanation matching, never an input to the primary model."""

from __future__ import annotations

import numpy as np
import pandas as pd

from prahari.data.firewall import assert_real, write_real_table
from prahari.eval.ablation import connected_case_groups
from prahari.explain.archetype import nearest_archetype
from prahari.explain.templates import archetype_text


def export_archetypes(config, predictions: pd.DataFrame, events: pd.DataFrame, peers: pd.DataFrame, arena: str) -> pd.DataFrame:
    """Use each case's first pre-event flag; exclude the focal case-peer component.

    The library is explicitly retrospective and cannot change historical scores.
    Unknown case-peer components produce no claimed eligible archetype.
    """
    cases = events.loc[events.needs_verification.eq(0)].set_index("entity_id")
    groups = connected_case_groups(peers.loc[peers.needs_verification.eq(0)])
    for entity in cases.index:
        groups.setdefault(entity, entity)
    frames = []
    for path in sorted((config.path("attributions") / arena).glob("*.parquet")):
        table = pd.read_parquet(path)
        assert_real(table)
        table = table.loc[table.horizon.eq("4q")]
        frames.append(table)
    if not frames:
        return pd.DataFrame()
    contributions = pd.concat(frames, ignore_index=True)
    vectors = contributions.pivot_table(index=["entity_id", "scoring_date"], columns="pillar", values="logit_contribution", aggfunc="sum", fill_value=0).reset_index()
    columns = list(config.section("pillars_config")["labels"])
    for column in columns:
        if column not in vectors:
            vectors[column] = 0.0
    first = []
    for entity, case in cases.iterrows():
        history = predictions.loc[predictions.entity_id.eq(entity) & predictions.deep_review.eq(1)
            & pd.to_datetime(predictions.scoring_date, utc=True).lt(pd.to_datetime(case.event_date, utc=True))]
        if history.empty:
            continue
        day = pd.to_datetime(history.scoring_date, utc=True).min().strftime("%Y-%m-%d")
        match = vectors.loc[vectors.entity_id.eq(entity) & vectors.scoring_date.astype(str).str.startswith(day)]
        if not match.empty:
            first.append({**match.iloc[0].to_dict(), "case_group": groups[entity]})
    library = pd.DataFrame(first, columns=["entity_id", "scoring_date", "case_group", *columns])
    rows = []
    for selected in predictions.loc[predictions.deep_review.eq(1)].itertuples():
        day = pd.Timestamp(selected.scoring_date).strftime("%Y-%m-%d")
        match = vectors.loc[vectors.entity_id.eq(selected.entity_id) & vectors.scoring_date.astype(str).str.startswith(day)]
        group = groups.get(selected.entity_id)
        result = nearest_archetype(selected.entity_id, group, match[columns].iloc[0].to_numpy(), library, columns) if group is not None and not match.empty else {
            "archetype": None, "distance": np.nan, "reason": "missing_sourced_case_group_or_attribution"}
        rows.append({"entity_id": selected.entity_id, "scoring_date": day, "arena": arena, **result,
                     "interpretation": "retrospective_explanation_similarity_not_historical_predictor", "is_synthetic": 0})
        memo = config.path("memos") / arena / day / (selected.entity_id + ".md")
        if memo.exists():
            text = memo.read_text(encoding="utf-8")
            marker = "\n## Retrospective archetype\n"
            text = text.split(marker)[0] + marker + archetype_text(result)
            memo.write_text(text, encoding="utf-8")
    result = pd.DataFrame(rows)
    if not result.empty:
        path = config.path("archetypes")
        if path.exists():
            previous = pd.read_csv(path)
            result = pd.concat([previous.loc[previous.arena.ne(arena)], result], ignore_index=True)
        write_real_table(result, path)
    return result
