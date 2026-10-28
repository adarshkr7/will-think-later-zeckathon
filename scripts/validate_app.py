"""Exercise the exported offline app and persist measured UI acceptance."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args()
    config = Config(args.config)
    os.environ["PRAHARI_APP_MANIFEST"] = str(config.path("app_manifest"))
    from streamlit.testing.v1 import AppTest
    start = time.perf_counter()
    app = AppTest.from_file(str(config.path("app_entrypoint")), default_timeout=30).run()
    cold = time.perf_counter() - start
    checks = {"cold_start_under_five_seconds": cold < 5,
              "four_tabs": len(app.tabs) == 4,
              "initial_render": not app.exception}
    def control(kind, label):
        return next(item for item in getattr(app, kind) if item.label == label)
    control("checkbox", "Reveal verified outcomes").check().run()
    checks["reveal_outcomes"] = not app.exception
    snapshots = __import__("pandas").read_parquet(config.path("app_snapshots"))
    entity = str(snapshots.entity_id.iloc[0])
    control("text_input", "ISIN, symbol or company").set_value(entity).run()
    checks["judge_search"] = not app.exception and control("selectbox", "Borrower").value == entity
    checks["memo_control"] = any(getattr(item, "label", None) == "Download memo" for item in app.get("download_button"))
    control("text_input", "ISIN, symbol or company").set_value("").run()
    for arena in snapshots.arena.unique():
        control("selectbox", "Arena").select(arena).run()
        checks["arena_" + arena] = not app.exception
    control("select_slider", "Scoring cutoff").set_value(str(snapshots.quarter.min())).run()
    checks["historical_cutoff"] = not app.exception
    payload = {"measured_at": __import__("pandas").Timestamp.now(tz="UTC").isoformat(),
               "cold_render_seconds": cold, "timing_scope": "AppTest construction and first render; Streamlit test-harness import excluded",
               "checks": checks, "passed": all(checks.values()), "is_synthetic": 0}
    config.path("ui_validation").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if not payload["passed"]:
        raise RuntimeError("Offline UI acceptance failed: " + str(checks))


if __name__ == "__main__":
    main()
