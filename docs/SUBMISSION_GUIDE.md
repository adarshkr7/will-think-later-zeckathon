# PRAHARI demonstration and submission

Start the interface from the project root with `./run_app.ps1`. It uses the existing Python 3.11 virtual environment and reads only exported files under `outputs/`. No exchange credentials, live API calls or model training are needed to demonstrate the exported interface.

If setting up another machine, install the pinned requirements into a Python 3.11 `.venv` first:

```powershell
py -3.11 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./run_app.ps1
```

The demo archive contains the app, code, configuration, public manual CSVs, tests and exported outputs. Public table names are explicitly whitelisted; sealed directories are never traversed. The original download cache and trained model cache stay local and are excluded from the archive. A full research rebuild requires those separate caches.

The interface exposes the two evaluation arenas, historical cutoffs, case search, outcome reveal, evidence and deterministic memo controls. The generated report is `docs/report/final_report.md`; its numerical claims trace to `outputs/report_trace.csv`.

For a source-backed walkthrough, select a case borrower, open Case Timeline and enable indicator history. Explore the exported liabilities/assets, profit/assets, current ratio, revenue growth or promoter-encumbrance observations. Missing inputs remain visible with their reasons. Policy & Metrics contains the development benchmark, current acceptance checks and the received-peer audit.

## Readiness and scientific results

The app manifest identifies the release mode. A readiness release demonstrates the working software and source-backed diagnostics while keeping unsupported Indian probability, recall and hit/miss results unavailable. It is not a completed registered evaluation. Current acceptance failures are listed in `outputs/panel_acceptance.csv`, and the delivery manifest includes them explicitly.

The received peer batches have a separate row-level source audit in `outputs/peer_intake_review.csv`, explained in `docs/intake/PEER_DATA_REVIEW.md`. Candidate names and current website values are not automatically verified historical observations. Original inputs are preserved separately.

`./run_all.ps1 -Offline -Readiness` rebuilds from the local caches. It verifies and restores the complete cached foreign development epoch when the learning code, settings, seed, training hashes, model hashes and original dependency pins remain valid. It then runs preparation, acceptance checks, fresh features, tests, the offline bundle, UI checks and report generation. Final benchmark and sealed Indian evaluation are not opened by readiness mode.

`./run_all.ps1 -Offline` retains the full scientific acceptance and registration boundaries. Do not bypass them or describe readiness output as a registered final result. Exported data and the app contain no synthetic company observations. Synthetic unit-test fixtures remain confined to `tests/fixtures/`.

## Delivery checks

Run `./run_tests.ps1`, inspect `outputs/ui_validation.json`, and generate the report from output artifacts. After these checks, `python -m scripts.11_package_demo` creates the offline demo archive and its SHA-256 receipt. `outputs/delivery_manifest.json` records engineering checks, source hashes, release mode and outstanding scientific gates.
