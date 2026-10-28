# Progress

Updated: 2026-10-28.

| Phase | Status | Acceptance evidence |
|---|---|---|
| 1 benchmark | doing | Development implementation and full run complete: 14 model tasks, 16 metric rows, 14 calibration tables/plots and outer-fold audits. Offline cached PowerShell rerun reproduced every output byte. Final hold-out acceptance intentionally pending; no reserved partition opened. |
| 2 panel collection | doing | Event-count and current identity/classification checks pass for all cases. Nine internal identifiers reconciled to sourced ISINs; reviewed classification import and subtotal/unit-aware statement extraction implemented. Peer membership, quotas and full historical coverage still fail. Current totals/checks are in outputs/collection_status.csv and outputs/panel_acceptance.csv. |
| 3 features | doing | Ratio, Altman/Hillegeist/Beneish/Piotroski, CHS, soft-signal and NBFC modules implemented. Hand-computed score tests pass. Assembly and full-quarter artifacts remain in progress; data acceptance is not waived. |
| 4 primary model / registration | todo | Zero-Indian-label override accepted. No preregistration lock created prematurely. |
| 5 Arena P replay / policy | todo | Awaiting verified panel and frozen configuration. |
| 6 explanations | todo | Awaiting model/replay. |
| 10 P0 signatures | todo | Awaiting replay. |
| 7 app | todo | P1 gated on P0 checks. |
| 8 report | todo | No manually entered performance claims. |

Latest pytest: **88 passed in 7.51s** via `run_tests.ps1`. Added hand-computed classical-screen and CHS tests, missing-input and financial-exemption checks. Feature assembly, production scoring and later phases remain in progress.

User steering: continue building all steps while data collection proceeds, push checkpoints to main, and keep project documentation under docs/. Implementation is proceeding through the remaining modules; acceptance gates, missing inputs, lock prerequisites and once-only final evaluations remain explicit. Historical market collection is running from the official archives with rate limits and cached receipts.

This session: accepted the user's verification of all 22 ticked checklist rows dated 2026-10-28. The company table now contains 12 verified labels and the component table contains those 22 rows plus two retained, previously sourced CIRP records. Unticked fields remain blank. The uncured-D rule is configured and applied uniformly, and RCom's original CIRP commencement is retained. The three supplied PDFs were registered with exact source URLs and checksums, moved under gitignored data/raw/manual/, and excluded from the commit. All linked PDFs are available offline with receipts.

Current follow-up: resolved all internal case IDs and sourced classifications from original company/CRA profiles. The import uses pinned document hashes and literal reviewed evidence, preserves identity publication bounds, and does not manufacture historical metadata. Human-verified event/public dates were compared against the preceding commit after key reconciliation and are unchanged. Every case symbol/ISIN agrees exactly with official NSE cache observations. Identity, classification and financial import commands have been rerun successfully.

Repeat-import check: all six affected manual evidence tables were byte-identical after rerunning identity reconciliation, classification extraction and financial extraction. The BSE sample was refreshed offline against the dated crosswalk. No benchmark refit, held-out evaluation, registration or Indian replay was performed in this follow-up.

`03_validate_manual --as-of 2018-09-30` writes current accounting, parity, financial-history, market and acceptance reports. It correctly exits nonzero because unique peers, peer quotas and full histories remain missing. Event count, current identity/classification, disjoint membership and known accounting identities pass. No overall Phase 2 acceptance is claimed, and no Indian scoring/replay has run.

The benchmark development run was rebuilt after the code/cache changes using the same splits, seed and predeclared grid. Its final development outputs are unchanged from the previous checkpoint. A cached offline rerun restored deliberately removed metrics/calibration tables and a calibration PNG byte-for-byte without fitting. The final-access ledger remains absent; no hold-out was opened.

Verified commands include the earlier benchmark development run/recovery and the current offline source collector, collection-status generator, tests and manual validator (expected nonzero result on the incomplete panel). Development metrics live in `outputs/benchmark_development_metrics.csv`; `outputs/benchmark_metrics.csv` does not exist because the final evaluator has not run. No Indian replay, pre-registration lock or sealed-case evaluation has occurred.

Latest implementation checkpoint: BSE fallback with a dated, source-backed crosswalk; quarterly-share-count market-cap joins; field-level annual-report extraction with pinned document hashes; sourced calendar and survivor-evidence schemas; and an explicit peer-selection publication command are implemented. Unknown leverage cannot qualify as an unstressed peer. The source collector publishes its catalog after processing the complete configured list.

Current totals are generated in `outputs/collection_status.csv`: 34 configured original PDFs cached, one unavailable annual-report source, and 118 verified financial-field observations across two entities. The evidence CSV also retains two unresolved dash cells as missing. Earlier ITNL statements and Alok's FY2017 statement tables have been reviewed and extracted. Comparative figures inherit the later source report's publication lag. Alok's post-event report does not increase its pre-event coverage. Market-cap values remain unknown without sourced quarterly share counts. `outputs/panel_acceptance.csv` still rejects the incomplete panel.

Verification after the later source changes: the complete cached NSE quarter and BSE sample work offline, reviewed extraction is idempotent, and the latest tests pass. The full benchmark run and byte-exact recovery described above preceded these later data-helper changes; it has not been refitted again for unrelated source-collection edits. No model-learning settings changed. Hold-outs, sealed cases and Indian replay remain untouched.

Open risks:

- The 12 labels are verified within the human-reviewed search, not proven earliest across every rating agency. Other-agency coverage and unticked event components remain incomplete. No matched peers or complete annual financial histories are available yet. Uncollected fields remain empty.
- All internal case keys are resolved and current classifications are sourced. Much of the metadata evidence was published after the matching quarter, however; historic classification/identity coverage must still be collected. The current catalog gate must not be confused with point-in-time peer eligibility.
- Current market cache is one initial quarter, not the required historical coverage. Missing source files do not prove holidays; a sourced session calendar and full panel windows are still needed. BSE identities without a verified crosswalk remain quarantined. TRI collection is pending; cached index rows are honestly marked price_index.
- Annual rows with unresolved source verification remain quarantined. Extracted financial evidence covers two entities and still lacks complete historical core fields. Quarterly share counts, peer financials and independently sourced peer-survival evidence are missing. Nonstandard eighteen-month reports are not being treated as ordinary annual flows.
- The original plan/literature mislabels Polish horizons. Configs use UCI's documented 5year/4year heads for 4Q/8Q, retaining 3year for comparison.
- Only ten ratio mappings are documented cleanly in both countries. Additional ratios remain null; no financial equivalences have been guessed.
- Final hold-out acceptance remains intentionally pending until development is frozen. Development outputs must never be presented as untouched hold-out performance.
- Exact downstream attribution through nonlinear probability calibration still needs a mathematically valid treatment in Phase 6; raw-margin SHAP values cannot simply be asserted to sum to calibrated log-odds.
- No Indian base-rate estimate is available yet; prior-shift code is tested but no Indian rate has been invented.
- P1/P2 work and the app remain gated on P0 acceptance. The current runner executes implemented phases only, not a complete historical replay.

Next three actions:
1. Collect metadata and standalone financials actually published before each event-minus-12Q matching cutoff; later business profiles cannot fill that historical gap.
2. Collect candidate/peer financial histories, independent survival evidence, sourced session calendars and share counts; select at least 30 unique matched peers under the configured rule. Keep sealed cases with an independent collector.
3. Pass the Phase 2 acceptance gate before Phase 3 ratio/forensic builders. Benchmark final evaluation, later primary scoring and replay remain pending; commit Indian pre-registration in its own commit before replay.
