"""Public evidence access through the same strict point-in-time boundary."""

from __future__ import annotations

import pandas as pd

from prahari.data.asof import as_of


def evidence_items(sources, entity_id: str, cutoff, previous=None) -> pd.DataFrame:
    rows = []
    for kind, table in sources.tables.items():
        visible = as_of(table, cutoff)
        visible = visible.loc[visible.entity_id.eq(entity_id)]
        if previous is not None:
            visible = visible.loc[visible.public_date.ge(pd.to_datetime(previous, utc=True))]
        for record in visible.to_dict(orient="records"):
            rows.append({"kind": kind, "public_date": record["public_date"],
                         "source_url": record.get("source_url") or record.get("source_doc"),
                         "field": record.get("field", kind), "is_synthetic": record["is_synthetic"]})
    result = pd.DataFrame(rows, columns=["kind", "public_date", "source_url", "field", "is_synthetic"])
    return result.drop_duplicates(["kind", "public_date", "source_url", "field"]).sort_values(["public_date", "source_url"], kind="stable")
