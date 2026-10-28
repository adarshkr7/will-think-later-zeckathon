# Progress

Updated: 2026-10-28.

| Phase | Status | Acceptance evidence |
|---|---|---|
| 1 benchmark | doing | Development implementation and full run complete: 14 model tasks, 16 metric rows, 14 calibration tables/plots and outer-fold audits. Offline cached PowerShell rerun reproduced every output byte. Final hold-out acceptance intentionally pending; no reserved partition opened. |
| 2 panel collection | doing | Seven schema-driven CSV templates initialized without records; strict schema/count validator and DATA_REQUESTS.md ready. Empty-panel acceptance correctly fails. |
| 3 features | todo | Point-in-time access boundary and its timing/restatement/imputation tests pass; actual financial feature builders remain pending. |
| 4 primary model / registration | todo | Zero-Indian-label override accepted. No preregistration lock created prematurely. |
| 5 Arena P replay / policy | todo | Awaiting verified panel and frozen configuration. |
| 6 explanations | todo | Awaiting model/replay. |
| 10 P0 signatures | todo | Awaiting replay. |
| 7 app | todo | P1 gated on P0 checks. |
| 8 report | todo | No manually entered performance claims. |

Latest pytest: **42 passed in 3.26s** via `run_tests.ps1`, including nested-fit spies, publication boundaries, restatements, conservative date lags, prior shift, cost threshold, calibration, target-country rank isolation, once-only evaluation claims, lock tampering, synthetic firewall and real cached-training integrity.

Verified commands: `run_all.ps1 -Offline` (full development run and byte-identical cached rerun), `run_all.ps1 -Offline -PrepareOnly`, direct `scripts/01_benchmark.py --help`, module entry points, and `03_validate_manual` (expected nonzero acceptance result on the empty panel). Development metrics live in `outputs/benchmark_development_metrics.csv`; `outputs/benchmark_metrics.csv` does not exist because the final evaluator has not run. No Indian replay, pre-registration lock or sealed-case evaluation has occurred.

Open risks:

- No verified Indian events, peers, annual financials, financial-sector metrics or soft signals. The empty-panel validator exits nonzero rather than treating missing observations as clean negatives.
- The original plan/literature mislabels Polish horizons. Configs use UCI's documented 5year/4year heads for 4Q/8Q, retaining 3year for comparison.
- Only ten ratio mappings are documented cleanly in both countries. Additional ratios remain null; no financial equivalences have been guessed.
- Final hold-out acceptance remains intentionally pending until development is frozen. Development outputs must never be presented as untouched hold-out performance.
- Exact downstream attribution through nonlinear probability calibration still needs a mathematically valid treatment in Phase 6; raw-margin SHAP values cannot simply be asserted to sum to calibrated log-odds.
- No Indian base-rate estimate is available yet; prior-shift code is tested but no Indian rate has been invented.
- P1/P2 work and the app remain gated on P0 acceptance. The current runner executes implemented phases only, not a complete historical replay.

Next three actions:
1. Collect verified panel evidence with the symmetric procedure in DATA_REQUESTS.md; keep independent sealed cases with their collector.
2. Complete panel normalization/coverage checks and asset-distance peer selection before scoring, then implement the point-in-time ratio/forensic features.
3. Build the zero-Indian-label primary overlay and Arena P replay; commit pre-registration in its own commit first. Keep benchmark final evaluation sealed until all modelling changes are finished.
