# PRAHARI

Point-in-time corporate credit early warning, built for Zeckathon PS-02.

## Submission files

- [Solution and results report (prahari_report.md)](docs/report/prahari_report.md) ([final_report.md](docs/report/final_report.md))
- [Demo walkthrough](docs/DEMO_SCRIPT.md)
- [Presentation outline](docs/slides_outline.md)

The generated report explains the method, implementation, benchmark results, review policy and limitations. Its numerical results trace to files under `outputs/`. Working research notes and collection plans are kept locally in gitignored `local_docs/`. README.md and AGENTS.md remain in the repository root.

## Run the offline app

From the project root on Windows, using Python 3.11:

```powershell
py -3.11 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./run_app.ps1
```

If the existing virtual environment is ready, run only `./run_app.ps1`. The interface reads exported outputs and performs no live scoring or exchange requests. It provides Time Machine, Case Timeline, Borrower Memo and Policy & Metrics tabs, historical cutoffs, company search and source-backed indicator histories.

## Current status

The foreign benchmark has completed development validation and its once-only untouched hold-out evaluation after a committed code/model freeze. Results are in `outputs/benchmark_development_metrics.csv` and `outputs/benchmark_metrics.csv`, with evaluation splits and confidence intervals.

Indian peer integration is deferred for this submission. Calibrated Indian probabilities, Indian recall and independent sealed results remain unavailable. The app labels its readiness state explicitly. `outputs/panel_acceptance.csv` and `outputs/run_status.csv` give the current gates; no early-detection claim is made for an Indian case.

## Reproduce and verify

```powershell
./run_tests.ps1
./run_all.ps1 -Offline -Readiness
```

A full cached rebuild additionally requires the local original-source and trained-model caches, which are excluded from GitHub and the demo archive. Strict execution with `./run_all.ps1 -Offline` preserves data acceptance and pre-registration checks. Final evaluations must never be reopened or used for tuning. Publication-dated Indian inputs pass through `as_of`; missing values remain explicit. Policy settings, including the review cap and error costs, live in `configs/policy.yaml`.

`outputs/test_summary.json` and `outputs/ui_validation.json` record checks. `outputs/feature_lineage_audit.csv` verifies the source epochs of the exported feature artifacts. `outputs/delivery_manifest.json` records the optional offline archive and file hashes. Build that archive with `python -m scripts.11_package_demo` from the prepared local checkout.

## Repository layout

- `prahari/`: data access, features, models, evaluation, policy and deterministic explanations.
- `scripts/`: pipeline stages and validation commands.
- `app/`: output-only Streamlit interface.
- `configs/`: settings and frozen benchmark lock.
- `data/manual/`: public canonical source-backed CSVs; private sealed inputs are excluded.
- `outputs/`: exported evidence, metrics, UI data and source hashes.
- `tests/`: tests and explicitly synthetic fixtures.
- `docs/`: submission documents only.

Raw downloads, received-file folders, local working notes, environments, credentials, model caches and local ZIPs are gitignored. Synthetic observations are confined to test fixtures and cannot enter production artifacts.

## Official submission

The organiser accepts the Markdown report as the explanation document. Submit it together with this repository link in both destinations:

- [Zeckathon submission form](https://docs.google.com/forms/d/e/1FAIpQLSfPaLvsicO3wvoOI9cgMeoAdfem5TKW1W93My6NIJtFs-ql8w/viewform?usp=header)
- [Zeckathon website](https://zeckathon.com/)

Submissions cannot be edited or replaced. The repository is public and should remain accessible until judging is complete. No external submission has been made by the implementation agent.
