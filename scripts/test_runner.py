"""Run pytest and record actual test outcomes for the report and offline app."""

import json
import argparse
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from prahari.config import Config


class Results:
    def __init__(self) -> None:
        self.outcomes = {}

    def pytest_runtest_logreport(self, report) -> None:
        if report.failed:
            self.outcomes[report.nodeid] = "failed"
        elif report.skipped:
            self.outcomes[report.nodeid] = "skipped"
        elif report.when == "call" and report.nodeid not in self.outcomes:
            self.outcomes[report.nodeid] = "passed"


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", default="configs/base.yaml")
    args, remaining = parser.parse_known_args()
    config = Config(args.config)
    results = Results()
    start = time.perf_counter()
    code = pytest.main(["-q", *remaining], plugins=[results])
    report = {"status": "passed" if code == 0 else "failed", "exit_code": int(code),
              "duration_seconds": time.perf_counter() - start,
              **{name: list(results.outcomes.values()).count(name) for name in ("passed", "failed", "skipped")}}
    path = config.path("test_summary")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    raise SystemExit(code)


if __name__ == "__main__":
    main()
