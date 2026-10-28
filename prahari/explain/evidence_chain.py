"""Production provenance adapter; missing counterfactual endpoints stay unknown."""

import copy

import numpy as np
import pandas as pd

from prahari.data.evidence import evidence_items
from prahari.data.firewall import write_real_table
from prahari.explain.provenance import telescoping_trace
from prahari.features.panel import build_features
from prahari.models.scoring import score_snapshot


def export_chains(config, sources, previous_features, previous_scores, features, scores, models, arena):
    current = features.attrs["as_of"]
    previous = previous_features.attrs["as_of"]
    tolerance = config.section("model_config")["explanation"]["tolerance"]
    for row in scores.loc[scores.deep_review.eq(1) & scores.pd_4q.notna()].itertuples():
        old = previous_scores.loc[previous_scores.entity_id.eq(row.entity_id)]
        if old.empty or pd.isna(old.iloc[0].pd_4q):
            continue
        items = evidence_items(sources, row.entity_id, current, previous).drop_duplicates(["kind", "public_date", "source_url"])
        def score_prefix(prefix):
            frozen = copy.copy(sources)
            frozen.tables = {}
            for name, table in sources.tables.items():
                dates = pd.to_datetime(table.public_date, utc=True)
                keep = dates.lt(pd.Timestamp(previous))
                new = table.entity_id.eq(row.entity_id) & dates.ge(pd.Timestamp(previous)) & dates.lt(pd.Timestamp(current))
                for item in prefix.loc[prefix.kind.eq(name)].itertuples():
                    url = table.source_url if "source_url" in table else table.source_doc
                    keep |= new & dates.eq(item.public_date) & url.eq(item.source_url)
                frozen.tables[name] = table.loc[keep]
            rebuilt = build_features(config, current, arena, sources=frozen)
            rescored, _ = score_snapshot(rebuilt, models, config.section("model_config"), arena)
            match = rescored.loc[rescored.entity_id.eq(row.entity_id), "pd_4q"]
            return match.iloc[0] if not match.empty else np.nan
        try:
            chain = telescoping_trace(items, previous, current, old.iloc[0].pd_4q, row.pd_4q, score_prefix, tolerance=tolerance)
            chain["status"] = "reconciled"
        except ValueError as exc:
            chain = pd.DataFrame([{"kind": "unavailable", "public_date": current, "source_url": None,
                "pd_before": old.iloc[0].pd_4q, "pd_after": row.pd_4q, "delta_pd": np.nan,
                "status": str(exc), "is_synthetic": int(items.is_synthetic.eq(1).any())}])
        chain["entity_id"], chain["scoring_date"], chain["arena"] = row.entity_id, current, arena
        path = config.path("provenance") / arena / pd.Timestamp(current).strftime("%Y-%m-%d") / (row.entity_id + ".parquet")
        write_real_table(chain, path)
