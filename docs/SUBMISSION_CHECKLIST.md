# Submission checklist against PS-02

This release is a working research prototype. The user has deferred peer integration for this delivery. It is upload-ready software with explicit incomplete research requirements; it does not claim full compliance with the Indian validation requirements.

| Required deliverable | Delivered evidence | Remaining limitation |
|---|---|---|
| Benchmark distress model and class-imbalance methodology | `outputs/benchmark_development_metrics.csv`, generated report, benchmark configuration and reproducible training code | Final-access status is recorded in `outputs/run_status.csv`; only results produced by the once-only evaluator may be called untouched hold-out results. |
| Indian case test and matched non-default peers | Reviewed event catalog, original-source financial evidence, financial/accounting/market audits, case cards | Peer integration is deferred. The minimum matched cohort and stressed-survivor acceptance requirements remain unmet; Indian recall is unavailable. |
| Manipulation and soft-signal screen | Guarded Altman, Beneish and Piotroski implementations; publication-dated ratings, promoter encumbrance and governance feature paths | Required source coverage is incomplete. Missing observations remain unknown and individual scores can be unavailable. |
| Credit-officer explanations | Deterministic memo templates, reconciled attribution and evidence-chain code; offline memo/evidence controls | Scored Indian explanations require accepted inputs and registered replay. Readiness memos state that a score is unavailable. |
| Operating policy and expected cost | `configs/policy.yaml`, `outputs/policy_parameters.csv`, generated cost calculation, deterministic ranking/cap and review workflow | A real Indian ranked watch-list and realised operational metrics require accepted calibration/data and replay. |

The generated report is `docs/report/final_report.md`; numerical claims trace to `outputs/report_trace.csv`. The report separates development, untouched benchmark evaluation and unrun Indian evaluation. All case cards retain unassessed status until genuine replay results exist.

## Files to provide

- Repository link and source commit on main.
- `dist/PRAHARI_offline_demo.zip` and its SHA-256 sidecar, uploaded separately because local delivery archives are gitignored.
- Generated report and `docs/slides_outline.md`.
- `docs/DEMO_SCRIPT.md` for the walkthrough and `docs/SUBMISSION_GUIDE.md` for setup.

The delivery manifest records actual tests, app checks, feature-source receipts and unresolved panel gates. Raw downloads, trained model caches, environments, private sealed inputs and received download folders are excluded from GitHub. Public canonical CSVs and source references remain reviewable.

## Claims to avoid

Do not claim that PRAHARI caught a named default early, achieved Indian recall, validated the full peer panel, or scored independent sealed cases. Those outcomes remain unassessed. Use the exported benchmark results with their stated evaluation split, base rates and confidence intervals. Missing data, retrospective reconstruction limits and unadjusted market observations are documented in the report.
