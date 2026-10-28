# Progress

Updated: 2026-10-28.

| Phase | Status | Acceptance evidence |
|---|---|---|
| 1 benchmark | doing | Development implementation and full run complete: 14 model tasks, 16 metric rows, 14 calibration tables/plots and outer-fold audits. Offline cached PowerShell rerun reproduced every output byte. Final hold-out acceptance intentionally pending; no reserved partition opened. |
| 2 panel collection | doing | Dated financial evidence, reviewed PDF extraction, NSE/BSE ingestion, market-cap joins, deterministic peer selection and explicit coverage/acceptance gates implemented. Current totals are in outputs/collection_status.csv. Two partial CIRP records remain unverified as earliest events; the panel acceptance gate remains unmet. |
| 3 features | todo | Point-in-time access boundary and its timing/restatement/imputation tests pass; actual financial feature builders remain pending. |
| 4 primary model / registration | todo | Zero-Indian-label override accepted. No preregistration lock created prematurely. |
| 5 Arena P replay / policy | todo | Awaiting verified panel and frozen configuration. |
| 6 explanations | todo | Awaiting model/replay. |
| 10 P0 signatures | todo | Awaiting replay. |
| 7 app | todo | P1 gated on P0 checks. |
| 8 report | todo | No manually entered performance claims. |

Latest pytest: **74 passed in 8.12s** via `run_tests.ps1`. Checks include benchmark/leakage/firewall coverage, restatement publication lags, explicit units and missing inputs, exchange identities, negative download caching, market-cap arithmetic, source-reviewed PDF parsing, financial-history windows and conservative peer/market coverage gates.

This session: official July–September 2018 NSE batch completed with original archives and checksummed receipts under the ignored raw cache. Offline sample market and PDF-collector commands pass. `outputs/collection_status.csv` records observed counts; `outputs/source_catalog.csv` indexes actual original documents. `03_validate_manual --as-of 2018-09-30` writes the accounting, parity and acceptance reports, then correctly exits nonzero: verified events 0/10 minimum, verified unique peers 0/30, financial histories and full panel market coverage absent. No Phase 2 acceptance has been claimed.

The benchmark development run was rebuilt after the code/cache changes using the same splits, seed and predeclared grid. Its final development outputs are unchanged from the previous checkpoint. A cached offline rerun restored deliberately removed metrics/calibration tables and a calibration PNG byte-for-byte without fitting. The final-access ledger remains absent; no hold-out was opened.

Verified commands: `run_all.ps1 -Offline` (full development run and byte-identical cached rerun), `run_all.ps1 -Offline -PrepareOnly`, direct `scripts/01_benchmark.py --help`, module entry points, and `03_validate_manual` (expected nonzero acceptance result on the empty panel). Development metrics live in `outputs/benchmark_development_metrics.csv`; `outputs/benchmark_metrics.csv` does not exist because the final evaluator has not run. No Indian replay, pre-registration lock or sealed-case evaluation has occurred.

Latest implementation checkpoint: BSE fallback with a dated, source-backed crosswalk; quarterly-share-count market-cap joins; field-level annual-report extraction with pinned document hashes; sourced calendar and survivor-evidence schemas; and an explicit peer-selection publication command are implemented. Unknown leverage cannot qualify as an unstressed peer. The source collector publishes its catalog after processing the complete configured list.

Current collection totals are generated in `outputs/collection_status.csv`: six original PDFs cached, one unavailable source, and 46 financial-field observations for one entity. Comparative figures inherit the later source report's conservative publication lag, rather than the comparative financial year's lag. The older cached ITNL report has not yet been reviewed for extraction. Missing annual-report values are not inferred. Market-cap values remain unknown where sourced quarterly share counts are absent. `outputs/panel_acceptance.csv` still rejects the incomplete panel.

Verification after the later source changes: the complete cached NSE quarter and BSE sample work offline, reviewed extraction is idempotent, and the latest tests pass. The full benchmark run and byte-exact recovery described above preceded these later data-helper changes; it has not been refitted again for unrelated source-collection edits. No model-learning settings changed. Hold-outs, sealed cases and Indian replay remain untouched.

Open risks:

- No verified earliest Indian events, matched peers, annual financial histories or financial-sector metrics. Two sourced CIRP components are incomplete labels, not verified earliest events. Uncollected fields remain empty.
- Current market cache is one initial quarter, not the required historical coverage. Missing source files do not prove holidays; a sourced session calendar and full panel windows are still needed. BSE identities without a verified crosswalk remain quarantined. TRI collection is pending; cached index rows are honestly marked price_index.
- Annual rows with unresolved source verification remain quarantined. Extracted financial evidence covers only one entity and does not satisfy complete historical core-field coverage. Entity classifications, quarterly share counts and independently sourced peer-survival evidence are still missing.
- The original plan/literature mislabels Polish horizons. Configs use UCI's documented 5year/4year heads for 4Q/8Q, retaining 3year for comparison.
- Only ten ratio mappings are documented cleanly in both countries. Additional ratios remain null; no financial equivalences have been guessed.
- Final hold-out acceptance remains intentionally pending until development is frozen. Development outputs must never be presented as untouched hold-out performance.
- Exact downstream attribution through nonlinear probability calibration still needs a mathematically valid treatment in Phase 6; raw-margin SHAP values cannot simply be asserted to sum to calibrated log-odds.
- No Indian base-rate estimate is available yet; prior-shift code is tested but no Indian rate has been invented.
- P1/P2 work and the app remain gated on P0 acceptance. The current runner executes implemented phases only, not a complete historical replay.

Next three actions:
1. Verify original event-source documents, including the newly supplied candidate-source guide; retain unresolved earliest-event records as unverified.
2. Continue public primary-source collection to verify at least 10 earliest events, 30 unique matched peers and their financial/market histories; keep sealed cases with an independent collector.
3. Pass the Phase 2 acceptance gate before Phase 3 ratio/forensic builders. Benchmark final evaluation, later primary scoring and replay remain pending; commit Indian pre-registration in its own commit before replay.
