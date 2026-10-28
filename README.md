# PRAHARI

Project documentation lives in docs/. Run commands from the repository root.

**P**oint-in-time **R**isk & **A**ccounting **H**azard **A**lerts, **R**anked & **I**nterpretable. *Prahari* is Hindi for "sentinel".

A submission for **Zeckathon PS-02 (Risk & Fraud)**: a point-in-time early-warning research system for Indian corporate credit. Detection performance remains unassessed until the data and registration gates pass.

## What it does

PRAHARI is a "credit-desk time machine". Pick any past quarter and it rebuilds what the market and filings showed on that date, using only documents published by then. The intended debt-ranked universe uses a market-only membership fallback while financial coverage is incomplete. Registered scoring produces a watch-list under the configured review cap and deterministic credit memos; the current readiness view leaves unscored probabilities and ranks blank. We then check which later defaulters were already flagged 4 and 8 quarters before default.

Key properties:

- **No look-ahead.** Every feature row carries a `public_date`; scoring at date *t* only sees rows published before *t*, enforced by tests.
- **Pre-registered evaluation.** Configs, weights and peer lists are hashed and committed before the first scored Indian replay. The reviewed public panel labels are already known; they never train the primary model.
- **Cost-optimal policy under a hard cap.** Threshold minimises `20·FN + FP` while never exceeding the 5% review budget.
- **Exact, auditable explanations.** Additive log-odds attributions grouped into credit pillars, rendered by deterministic templates. No LLMs in the pipeline.
- **Separate scorecard for financial firms** (NBFCs, HFCs), where Altman/Beneish don't apply.

## Repository guide

| File | Purpose |
|---|---|
| `docs/ps.pdf` | Problem statement and judging criteria |
| `docs/PROJECT_IDEA.md` | What we are building and why |
| `docs/IMPLEMENTATION_PLAN.md` | Phases, modules, tests and acceptance checks |
| `AGENTS.md` | Operating rules for coding agents working on this repo |

## Status

Phase 1 development is implemented: cached UCI ingestion, sealed stratified partitions, fold-local preprocessing, nested cross-validation, unweighted/weighted LightGBM, logistic regression, out-of-fold calibration, monotone harmonized models and a cross-country transfer test. Final benchmark hold-outs remain unopened. Development results are explicitly distinguished from final results.

Phase 2 has public-source caching, reviewed financial-field extraction, NSE/BSE ingestion, dated market-cap joins, peer selection and explicit acceptance checks. Panel evidence remains incomplete. Dated feature builders, frozen primary scoring, capped replay, separate OOF ablations, explanation/memo exports, a four-tab app and a generated report are implemented. Production acceptance and Indian performance remain gated. See [PROGRESS.md](docs/PROGRESS.md) and [DATA_REQUESTS.md](docs/DATA_REQUESTS.md).

Build the cached incomplete-data demo and launch it:

```powershell
./run_all.ps1 -Offline -Readiness
./run_app.ps1
```

Readiness mode preserves missing values and makes no hit/miss claims. Strict `./run_all.ps1 -Offline` stops on incomplete panel acceptance. When the data gate eventually passes, the runner freezes and commits the Indian registration lock alone before replay. Final benchmark and sealed-envelope openings are always separate explicit commands. The app reads exported files under `outputs/` only; all documentation except this README and AGENTS.md lives under `docs/`.

**Horizon correction:** UCI documents `5year.arff` as a one-year forecast and `4year.arff` as two years. The benchmark retains `3year` and `4year` comparisons, and uses `5year`/`4year` for the intended 4Q/8Q HDM heads. The original plan's horizon labels are off by one year. Source: [UCI Polish dataset documentation](https://archive.ics.uci.edu/dataset/365/polish+companies+bankruptcy+data).

## Environment

Windows 11, Python 3.11, virtualenv at `.venv`.

```powershell
uv python install 3.11
uv venv --python 3.11 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
.\run_tests.ps1
.\run_all.ps1                  # Current implemented phases, downloads cached once
.\run_all.ps1 -Offline         # Reuses official downloads and verified model artifacts
.\run_all.ps1 -Offline -PrepareOnly
```

The full benchmark grid is deliberately substantial. Completed tasks are cached with code/config/data fingerprints in separate generation directories. A changed fingerprint creates a fresh generation, preserving earlier models and reserved partitions. Cached runs restore metric/calibration tables and missing calibration plots without refitting. Do not delete or recreate reserved partitions.

```powershell
.venv/Scripts/python.exe -m scripts.01_benchmark --offline
.venv/Scripts/python.exe -m scripts.03_validate_manual --init-templates
.venv/Scripts/python.exe -m scripts.03_validate_manual
```

Phase 2 public-source commands:

```powershell
.venv/Scripts/python.exe -m scripts.02_market_data --sample
.venv/Scripts/python.exe -m scripts.02_market_data --sample --offline
.venv/Scripts/python.exe -m scripts.02_market_data --start 2018-07-01 --end 2018-09-30
.venv/Scripts/python.exe -m scripts.02b_collect_sources
.venv/Scripts/python.exe -m scripts.02b_collect_sources --offline
.venv/Scripts/python.exe -m scripts.02d_extract_financials
.venv/Scripts/python.exe -m scripts.03d_apply_identities
.venv/Scripts/python.exe -m scripts.03e_extract_metadata
.venv/Scripts/python.exe -m scripts.02c_market_cap --as-of 2018-09-30
.venv/Scripts/python.exe -m scripts.03c_collection_status
.venv/Scripts/python.exe -m scripts.03_validate_manual --as-of 2018-09-30
```

The market collector uses the configured historical range when no dates are supplied; collecting that entire range is a substantial rate-limited job. It retains original zipped downloads and receipts under `data/raw/`, with parsed session caches under `data/interim/market/`. Missing official files are logged as unknown gaps, never inferred to be holidays. The offline sample command uses only existing archives; an offline range containing uncached dates fails explicitly. A complete sourced exchange calendar is still required for the market-coverage acceptance audit. The index archive is explicitly tagged as a price index, not TRI.

Repeated exchange blocks stop collection and persist a manual request. To register an actual manually downloaded archive without overwriting raw data:

```powershell
.venv/Scripts/python.exe -m scripts.02_market_data --import-file <local-file> --import-url <original-source-url> --import-source nse
```

`03_validate_manual` writes accounting, financial-history, market-coverage and panel acceptance checks. Its optional as-of audit writes `outputs/coverage_parity.csv`; empty cohorts are unresolved. Collection progress is in `outputs/collection_status.csv`, and original PDFs are indexed in `outputs/source_catalog.csv`. Human-verified event labels are imported with component publication dates in `data/manual/event_evidence.csv`; unknown components and classifications stay blank. The cured-D exclusion applies to every company. Complete historical coverage, security/classification metadata and independently sourced peer eligibility remain outstanding.

Market collection supports `--exchange auto`, `nse` or `bse`. Unmapped BSE identities remain quarantined. Market caps require dated quarterly share counts; missing counts remain unknown. The financial extractor uses only reviewed statement mappings and pinned document hashes, preserving later publication dates for comparative figures. `scripts.03b_select_peers --write-peers` publishes eligible matches only after its data checks pass and refuses changes after registration. It currently fails on the incomplete event cohort, as intended.

Template initialization never overwrites an existing file. The validator rejects an empty panel at the acceptance gate. The full historical pipeline is not yet implemented; `run_all.ps1` announces that it runs implemented phases only.

Identity reconciliation reads the configured manual tables only, preserves event and publication dates, and refuses changes after registration. Classification imports verify pinned source bytes and reviewed profile text; their public date includes the later identity proof. A current classification does not imply availability at an earlier peer-matching cutoff. Older statements use explicit denomination and reviewed subtotal positions. Cash alone and finance costs remain separate reported inputs.

Development artifacts:

- `outputs/benchmark_development_metrics.csv`: nested outer-fold metrics plus separately marked transfer development results; PR-AUC is average precision, with trapezoidal PR area also recorded.
- `outputs/benchmark_audit.json`: outer-fold row counts, selected parameters and fit/validation overlap assertions.
- `outputs/benchmark_calibration/`: reliability tables and plots.
- `data/interim/models/`: local serialized models and task receipts, git-ignored.
- `outputs/manual_validation.csv`: actual input coverage counts, including empty inputs.

Uncertainty intervals are row-bootstrap intervals conditional on fitted predictions, not intervals over model selection or correlated firm histories. Polish files have neither usable row timestamps nor company identifiers, so these splits are not claimed to be temporal or entity-disjoint. Taiwan ratio values are normalized: transfer uses a separate unlabelled Taiwan-training-only rank reference, frozen with the Polish model. No target hold-out covariates fit it. Taiwan's forecast horizon is unspecified in the source; `horizon_quarters` describes the Polish source model, and the transfer result is not claimed to validate that horizon in Taiwan. Production SMOTE is excluded under the synthetic-data rule in AGENTS.md.

Final evaluation is a separate, irreversible evaluation step, intentionally excluded from `run_all.ps1`. Once development is complete, freeze the benchmark and commit its lock before opening it:

```powershell
.venv/Scripts/python.exe -m prahari.eval.seal --freeze-benchmark
# Commit configs/benchmark.lock and finish all intended modelling changes first.
.venv/Scripts/python.exe -m prahari.eval.seal --final
```

The final command verifies code/config/model/training hashes, atomically claims the evaluation once, validates reserved values against the cached official source, and writes `outputs/benchmark_metrics.csv`. It never prints reserved membership. A failed run consumes its claim too; no flag bypasses the once-only guard. Subsequent development is rejected. The separate Indian `configs/preregistration.lock` must be created and committed in its own commit before the later replay phase; it has not been created prematurely.
