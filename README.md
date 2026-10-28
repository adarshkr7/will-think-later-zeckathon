# PRAHARI

**P**oint-in-time **R**isk & **A**ccounting **H**azard **A**lerts, **R**anked & **I**nterpretable. *Prahari* is Hindi for "sentinel".

A submission for **Zeckathon PS-02 (Risk & Fraud)**: an early-warning system for Indian corporate credit that would have caught IL&FS.

## What it does

PRAHARI is a "credit-desk time machine". Pick any past quarter and it rebuilds what the market and filings showed on that date, using only documents published by then. It ranks ~800 indebted listed borrowers and produces a watch-list capped at 5% of the universe, each name with a short, template-generated credit memo. We then check which later defaulters were already flagged 4 and 8 quarters before default.

Key properties:

- **No look-ahead.** Every feature row carries a `public_date`; scoring at date *t* only sees rows published before *t*, enforced by tests.
- **Pre-registered evaluation.** Configs, weights and peer lists are hashed and committed before Indian labels are read.
- **Cost-optimal policy under a hard cap.** Threshold minimises `20·FN + FP` while never exceeding the 5% review budget.
- **Exact, auditable explanations.** Additive log-odds attributions grouped into credit pillars, rendered by deterministic templates. No LLMs in the pipeline.
- **Separate scorecard for financial firms** (NBFCs, HFCs), where Altman/Beneish don't apply.

## Repository guide

| File | Purpose |
|---|---|
| `ps.pdf` | Problem statement and judging criteria |
| `PROJECT_IDEA.md` | What we are building and why |
| `IMPLEMENTATION_PLAN.md` | Phases, modules, tests and acceptance checks |
| `AGENTS.md` | Operating rules for coding agents working on this repo |

## Status

Phase 1 development is implemented: cached UCI ingestion, sealed stratified partitions, fold-local preprocessing, nested cross-validation, unweighted/weighted LightGBM, logistic regression, out-of-fold calibration, monotone harmonized models and a cross-country transfer test. Final benchmark hold-outs remain unopened. Development results are explicitly distinguished from final results.

Panel input templates and validation are available. Indian panel collection, feature layers, the primary scoring overlay, replay, memos, app and report remain pending. See [PROGRESS.md](PROGRESS.md) for acceptance status and [DATA_REQUESTS.md](DATA_REQUESTS.md) for the missing source evidence.

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

The full benchmark grid is deliberately substantial. Completed tasks are cached with code/config/data fingerprints; a changed fingerprint refuses stale artifacts rather than silently reusing them. Set a new configured model directory before a fresh development run if the modelling implementation changes. Do not delete or recreate reserved partitions.

```powershell
.venv/Scripts/python.exe -m scripts.01_benchmark --offline
.venv/Scripts/python.exe -m scripts.03_validate_manual --init-templates
.venv/Scripts/python.exe -m scripts.03_validate_manual
```

Template initialization never overwrites an existing file. The validator rejects an empty panel at the acceptance gate. The full historical pipeline is not yet implemented; `run_all.ps1` announces that it runs implemented phases only.

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
