"""Import source-reviewed classifications without backdating matching metadata."""

import argparse
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.data.entity_review import merge_reviewed_entities, reviewed_entities
from prahari.data.firewall import write_real_table
from prahari.data.manual import read_manual
from prahari.data.quality import validate_table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    if config.path("preregistration_lock").exists():
        raise RuntimeError("Classification is registered; amendment required")
    fresh = reviewed_entities(config, pd.Timestamp.now(tz="UTC"))
    current = read_manual(config, "entities")
    for frame in (fresh, current):
        for column in ("period_end", "public_date"):
            frame[column] = pd.to_datetime(frame[column], utc=True)
    combined = merge_reviewed_entities(current, fresh)
    events = read_manual(config, "events")
    latest = fresh.sort_values("public_date").drop_duplicates("entity_id", keep="last").set_index("entity_id")
    for field in ("sector", "is_financial"):
        values = events.entity_id.map(latest[field])
        conflict = events[field].notna() & values.notna() & events[field].ne(values)
        if conflict.any():
            raise ValueError("Reviewed classification disagrees with the existing event catalog")
        events[field] = events[field].fillna(values)
    settings = config.section("manual_config")
    validate_table(combined, "entities", settings)
    validate_table(events, "events", settings)
    for name, frame in (("entities", combined), ("events", events)):
        for flag in settings["tables"][name]["flags"]:
            frame[flag] = frame[flag].astype("Int64")
        write_real_table(frame, config.path("manual") / f"{name}.csv")


if __name__ == "__main__":
    main()
