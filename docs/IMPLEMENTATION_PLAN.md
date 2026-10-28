# PRAHARI: implementation plan (for Codex)

Read `PROJECT_IDEA.md` first. This file is the build spec. Priorities:
- **P0** must exist for submission.
- **P1** makes it strong.
- **P2** is polish.

Do the phases in order. Every phase ends with acceptance checks that must pass.

---

## 0. Global rules (apply everywhere)

1. **Python 3.11.** Libraries:
   - Data and IO: `pandas`, `numpy`, `pyarrow`, `requests`, `beautifulsoup4`.
   - Modelling: `scipy`, `scikit-learn`, `lightgbm`, `shap`, `imbalanced-learn`.
   - App and plots: `streamlit`, `plotly`.
   - Tooling: `pytest`, `pydantic`, `pyyaml`, `tqdm`.
   - Pin versions in `requirements.txt`.
2. **Seeds.** Use one global seed (`42`) set in `configs/base.yaml`.
3. **No leakage, ever.**
   - Every table holding Indian data must have the columns `entity_id`, `public_date` (date the value became public), and `period_end`.
   - All feature access goes through `prahari.data.asof.as_of(table, t)`, which returns only rows where `public_date < t`, keeping the latest row per (entity, field).
   - Direct reads of raw tables inside feature or model code are forbidden. A test greps for this.
4. **Preprocessing fit discipline.** Any fitted preprocessing (imputers, winsor bounds, scalers, rank tables) is fit on training folds only, or on the cross-section at date *t* only.
5. **Data provenance.** Every hand-collected value has a `source_url` or `source_doc` column.
6. **Outputs.** Write outputs to `outputs/` as parquet/CSV plus PNG/HTML figures. Never overwrite raw data.

## 1. Repository layout

```
prahari/
  configs/            base.yaml, benchmark.yaml, india.yaml, policy.yaml, preregistration.lock
  data/
    raw/              downloaded files, untouched
    manual/           hand-collected CSVs (templates in §3)
    interim/  processed/
  prahari/
    data/             asof.py, uci.py, bhavcopy.py, financials.py, shareholding.py,
                      ratings.py, events.py, universe.py, quality.py
    features/         ratios.py, harmonize.py, forensic.py (altman, beneish, piotroski, hillegeist),
                      chs.py, soft.py, nbfc.py, panel.py
    models/           benchmark.py, hdm.py, stacker.py, calibrate.py, prior_shift.py
    policy/           threshold.py, watchlist.py, cost.py
    explain/          attribution.py, pillars.py, templates.py, archetype.py
    eval/             metrics.py, replay.py, ablation.py, seal.py, report.py
  app/                streamlit_app.py (+ pages/)
  scripts/            01_benchmark.py … 09_build_report.py
  tests/
  outputs/
  report/             final_report.md (auto-filled tables), slides outline
```

---

## Phase 1 (P0): benchmark distress model (deliverable 1)

**Steps**
1. `prahari/data/uci.py`
   - **Polish.** Download UCI dataset 365 (the zip of `1year.arff` … `5year.arff`). Parse with `scipy.io.arff`, decode the class bytes into 0/1, and keep a `horizon_file` column.
   - **Taiwan.** Download UCI dataset 572, via `ucimlrepo` or the CSV.
   - **Checks.** Assert the row counts and positive counts. The expected values for Polish are 4year ≈ 9,792 rows with 515 positives, and 3year ≈ 10,503 rows with 495 positives. Taiwan has 6,819 rows and 220 positives. Log any mismatch.
2. **Untouched hold-out.**
   - Make a stratified 80/20 split for each dataset or horizon. Save the hold-out indices to `data/processed/holdout_<ds>.json` along with their SHA-256 hash.
   - `eval/seal.py` keeps a counter, and opening a hold-out twice raises an error unless `--final` is passed.
3. **Pipeline.** `models/benchmark.py` builds a pipeline whose steps are all fit inside the folds:
   - median imputation plus missing-value indicators
   - winsorization at the 1st/99th percentile
   - dropping one feature from each pair with |r| > 0.8
   - LightGBM

   Then:
   - **Tuning.** Use nested 5-fold stratified CV: an inner Optuna-free grid of about 12 configurations, and an outer loop for reporting.
   - **Imbalance variants.** Compare (a) `scale_pos_weight = neg/pos`, (b) SMOTE inside the folds only, and (c) no reweighting. Also train a logistic-regression baseline.
4. **Calibration.** In `models/calibrate.py`, fit isotonic regression on out-of-fold predictions; use Platt scaling if there are fewer than 50 positives. Report Brier score, ECE (10 bins), and a reliability plot.
5. **Hold-out metrics** (`eval/metrics.py`), for each dataset:
   - PR-AUC with a 1,000-resample bootstrap 95% CI
   - ROC-AUC
   - the base rate
   - Recall@5% and Precision@5%
   - cost-optimal τ on a grid from 0.01 to 0.5, plus the cost at τ\* = 1/21

   Write `outputs/benchmark_metrics.csv`.
6. **Harmonized feature set** (`features/harmonize.py`).
   - **Mapping table.** Write `configs/harmonized_map.yaml`, mapping a canonical ratio to its Polish attribute and its Taiwan column.
   - **Canonical ratios:** ROA, TL/TA, WC/TA, CA/CL, quick ratio, RE/TA, EBIT/TA, Equity/TL, Sales/TA, (GP+Dep)/TL, CL/TA, Sales growth, Equity/TA, Cash/TA, plus any others that are clean.
   - **Verify the Polish attribute definitions** against the UCI attribute list; don't trust memory. Polish Attr1 = net profit/TA, Attr2 = TL/TA, Attr3 = WC/TA, Attr4 = CA/ST liabilities, Attr6 = RE/TA, Attr7 = EBIT/TA, Attr8 = BV equity/TL, Attr9 = sales/TA, Attr10 = equity/TA, Attr16 = (GP+dep)/TL, Attr46 = (CA−inventory)/ST liab, Attr51 = ST liab/TA, Attr21 = sales growth.
   - **Drop absolute-size features** (e.g. log TA in PLN).
   - **Rank transform.** Convert each ratio to a percentile rank within its cross-section: the horizon file for Polish, the dataset for Taiwan, and the quarter universe for India.
7. **HDM** (`models/hdm.py`). Train LightGBM on harmonized ranks for Polish 4year (target `pd_4q`) and 3year (`pd_8q`). Then:
   - Set `monotone_constraints` from the economic sign stored in the mapping YAML.
   - Calibrate on out-of-fold predictions.
   - **Cross-country transfer test.** Score the Taiwan harmonized features with the model and report PR-AUC. This is the genuine out-of-sample result.
8. **Prior shift** (`models/prior_shift.py`). Rescale with
   `p' = (p·π_new/π_old) / (p·π_new/π_old + (1−p)(1−π_new)/(1−π_old))`.
   `π_new` comes from `configs/india.yaml` (the default-rate estimate of the Indian universe, computed in Phase 3).

**Acceptance**
- `outputs/benchmark_metrics.csv` has rows for Polish-4y, Polish-3y, Taiwan, transfer(Polish→Taiwan), and the HDM variants.
- A test checks that no transform is fit on hold-out rows: mock the transformer and assert the indices it was fit on.

---

## Phase 2 (P0): Indian data collection (deliverable 2). Start this in parallel with Phase 1 because it is the critical path.

### 2.1 Manual CSV templates (in `data/manual/`, with a pydantic schema validated in `data/quality.py`)

**`events.csv`**
- `entity_id`, `name`, `nse_symbol`, `bse_code`, `isin`, `sector`, `is_financial`
- `first_payment_default_date`, `first_D_rating_date`, `cirp_admission_date`, `event_date` (the earliest of the three)
- `source_urls`, `notes`

**`peers.csv`**
- `entity_id`, `name`, `symbols`, `sector`, `is_financial`, `matched_to`, `is_stressed_survivor`, `selection_rule_version`

**`annual_financials.csv`** (one row per entity × FY × basis, where basis is standalone or consolidated)
- Keys: `entity_id`, `fy_end`, `basis`
- Balance sheet: `total_assets`, `total_liabilities`, `current_assets`, `current_liabilities`, `inventory`, `receivables`, `cash_and_st_investments`, `ppe_net`, `cwip`, `total_debt`, `st_borrowings`, `commercial_paper`, `lt_debt`, `equity`, `retained_earnings`
- P&L: `revenue`, `cogs`, `gross_profit`, `sga`, `depreciation`, `ebit`, `interest_expense`, `pbt`, `pat`
- Other: `cfo`, `shares_outstanding`
- Related parties: `related_party_loans_advances`, `related_party_revenue`
- Audit and timing: `auditor_opinion` (`clean`/`qualified`/`adverse`/`disclaimer`), `going_concern_flag`, `caro_default_flag`, `caro_fraud_flag`, `results_public_date`, `annual_report_public_date`
- Provenance: `source_doc`

**`nbfc_metrics.csv`** (financials only, quarterly or half-yearly)
- `entity_id`, `period_end`, `public_date`, `gnpa_pct`, `nnpa_pct`, `car_pct`, `nim_pct`, `cp_share_of_borrowings`, `st_liab_to_st_assets`, `loan_book_growth`, `source_doc`

**`shareholding.csv`** (quarterly)
- `entity_id`, `period_end`, `public_date`, `promoter_holding_pct`, `promoter_pledged_pct_of_promoter`, `source_url`

**`rating_actions.csv`**
- `entity_id`, `agency`, `action_date`, `instrument`, `rating_from`, `rating_to`, `outlook`, `watch`, `inc_flag`, `is_default_grade`, `source_url`

**`governance_events.csv`**
- `entity_id`, `event_type` (one of `auditor_resignation`, `delayed_results`, `cfo_resignation`, `forensic_audit_ordered`), `announce_date`, `detail`, `source_url`

### 2.2 Collection procedure
1. **Defaulters.** Collect ≥ 12 (the list is in PROJECT_IDEA §4). Verify each date from IBBI/NCLT orders, CRA press releases and exchange disclosures. Collect data for FY(event−4) through FY(event); scoring only uses what was public before each *t*.
2. **Peer selection** (`features/panel.py::select_peers`).
   - Pick ≥ 3 peers per defaulter from the same sector, closest by total assets at event−12Q.
   - **Hard negatives.** At least a third must be stressed survivors: sector-top-quartile TL/TA and no default within 8 quarters.
   - Run the selection **before** Phase 5. Write `peers.csv` and record the rule version.
3. **Market data** (`data/bhavcopy.py`).
   - Download NSE (and BSE as fallback) daily bhavcopy archives for FY2012–FY2024. The `jugaad-data` package or direct archive URLs work. These include delisted symbols, so there is no survivorship bias.
   - Also download Nifty 500 TRI (fallback: Nifty 50).
   - Cache to parquet.
   - Handle symbol changes and suspensions: forward-fill prices for at most 5 days, otherwise mark them missing.
4. **Market cap** = close × shares outstanding, using the latest shareholding filing with `public_date < t`.

### 2.3 Background universe (`data/universe.py`), P0 with fallbacks
- **Target.** Each quarter-end *t*, the universe U_t is the ~800 firms with the largest total debt (from the latest public annual data) among firms traded on NSE/BSE at *t*. Panel firms are always included.
- **Source of background financials, in order of preference:**
  1. CMIE Prowess, if the team has institutional access.
  2. Screener.in Excel exports (10y annual). Download these manually or with a logged-in session cookie supplied by the user via an env var. Rate-limit to ≤ 1 request every 3 seconds and respect ToS.
  3. NSE XBRL financial results via the corporate-filings API. This includes broadcast timestamps, which is the best source for point-in-time dating.
  4. **Last resort:** a market-only background (CHS layer only) built from bhavcopy for all traded firms. The alert rate is then still measured against a realistic N, and we document the limitation.
- **Missing filing dates.** If background data has no `public_date`, apply the conservative lag: FY-end + 90 days for results fields, + 180 days for annual-report fields.
- **Background defaulters.** Cross-check every background firm against the IBBI list of CIRP cases for listed companies and CRA 'D' ratings. Matches get `label_source = background_verified`. Unlabeled firms are assumed non-default.

### 2.4 Data checks (`data/quality.py`, P0)
- **Schema validation.** Validate every manual CSV against its schema.
- **Accounting identities.** Assets ≈ liabilities + equity within 2%. Report the coverage table.
- **Coverage-parity test.** Compare missingness rates per feature between defaulters and non-defaulters with a Fisher exact test. A feature with p < 0.05 **and** collection-induced missingness is excluded from the universe model and kept in panel mode only. Output `outputs/coverage_parity.csv`.

**Acceptance**
- ≥ 10 verified events with source URLs.
- ≥ 30 peers.
- Bhavcopy cache covers all panel firms.
- `quality.py` passes.

---

## Phase 3 (P0): feature engineering (deliverable 3)

All features are computed by `features/panel.py::build_features(t)`. It calls `as_of` only, and emits one row per entity in U_t with a `max_source_date` column.

1. **`ratios.py`.** Harmonized ratios matching Phase 1, standalone basis by default. Also:
   - consolidated/standalone debt multiplier
   - ALM mismatch = (ST borrowings + CP) / (cash + receivables)
   - CWIP/TA
   - interest coverage
2. **`forensic.py`.**
   - **Altman Z.** Classic (manufacturing) and Z'' EM (`3.25 + 6.56X1 + 3.26X2 + 6.72X3 + 1.05X4`).
   - **Hillegeist updated Z.**
   - **Beneish M.** All 8 variables using year *y* vs *y−1*, guarding against division by zero. The flag is M > −1.78.
   - **Piotroski F.** 9 binary signals.
   - **Cash-conversion gap** = (PAT − CFO)/TA.
   - **Financial firms.** For `is_financial` firms all of these are NaN, plus an `na_reason` column.
3. **`chs.py`.** For quarterly scoring we use annual NI/4 or the latest TTM, documented.
   - MTA = TL + ME
   - NIMTA, TLMTA, CASHMTA
   - NIMTAAVG with φ = 2^(−1/3) over the last 4 quarterly values
   - EXRETAVG: 12-month geometric-weighted log excess return vs the index
   - SIGMA: annualized stdev of daily returns over 3 months
   - RELSIZE = log(ME / total market cap of the universe)
   - MB = ME / book equity, with negative book equity floored
   - PRICE = log(min(price, cap)); the cap is set in config
   - CHS score with the published coefficients from the research report, stored in `configs/base.yaml`
   - Unit-test each formula on a toy example.
4. **`soft.py`.**
   - `pledge_pct`, `pledge_delta_4q`, `psp_interaction = pledge × TLMTA × max(0, −NIMTAAVG)`
   - `auditor_exit_8q` (binary, last 8 quarters)
   - `rating_notch_delta_4q`, using an ordinal map from AAA = 1 to D = 22 with CRISIL/ICRA/CARE/IndRa aligned
   - `rating_watch_neg_or_inc`
   - `delayed_filing_4q`
   - `audit_red_flag_count`
   - `governance_flag_count`
5. **`nbfc.py`** (financials track).
   - **Inputs:** leverage (TA/equity), CP share, ST-liability/ST-asset gap, GNPA level and Δ, CAR headroom over the regulatory minimum, NIM Δ, and loan-growth anomaly vs peers.
   - **Score:** a fixed, pre-registered monotone scorecard. Each input becomes a percentile rank among the financial firms in U_t; the score is the weighted sum with weights in `configs/india.yaml`.
6. **Labels.** `y_4q(i,t) = 1` if event_date ∈ (t, t+4Q]; `y_8q` likewise for (t, t+8Q]. Labels are used **only** in `eval/` and in the stacker's CV fitting.
7. **Leakage test** (`tests/test_leakage.py`). For a random sample of (entity, t), assert `max_source_date < t`. Also check that no feature column changes when every row with `public_date ≥ t` is deleted from the raw tables.

**Acceptance**
- `data/processed/features_<quarter>.parquet` exists for every quarter-end from FY2014-Q1 to FY2024-Q4.
- The leakage tests pass.
- The forensic-score unit tests pass.

---

## Phase 4 (P0): stacker, calibration, pre-registration

> **OVERRIDE (see PROJECT_IDEA §8b).**
> - **Primary model:** the zero-Indian-label model. It combines the HDM logit (prior-shifted), a standardized CHS score, and a soft-signal overlay whose fixed log-odds weights live in `configs/india.yaml`. The defaults are: auditor exit +1.5, rating watch-negative/INC +1.0, each rating notch down +0.3, pledge Δ4Q > 20pp +0.7, delayed filing +0.7, going-concern/CARO default +1.5. Final calibration uses only the prior-shift formula; no Indian labels are used.
> - **Stacker:** the steps below are **ablation only**.
> - **Arenas:** all metrics are reported separately for Arena U (uniformly collected features only) and Arena P (matched panel, full features).
> - **Phase 5 additions:**
>   - recall broken down by period and by sector
>   - a placebo test (shuffle event dates within each firm, 100 runs)
>   - naive baselines: Altman only, rating-downgrade only, 52-week drawdown only
>
> **Build order for the MVP:** Phase 1 → Phase 2 (panel only) → 3 → 4 → 5 (Arena P) → 6 → 7. Arena U is built in parallel and is never on the critical path.

1. **Component logits.** `hdm_logit` (from the Phase 1 model applied to Indian rank features, prior-shifted), `chs_score`, `z_em`, `m_score`, `f_score`, `pledge_composite`, `rating_composite`, `gov_flag_count`. Financial firms use `nbfc_score` in place of HDM and the forensic inputs.
2. **Stacker** (`models/stacker.py`). Logistic regression, L2, with input signs constrained by refitting with a sign-flip penalty or by `scipy.optimize` with bounds. There are separate heads for `y_4q` and `y_8q`.
   - **Training rows:** universe firm-quarters from FY2014–FY2019 that are not in the evaluation fold.
   - **CV:** leave-one-case-group-out, where a group is a defaulter plus its peers. Background firms are split by `entity_id` hash into the same folds.
   - All reported Indian predictions are **out-of-fold**.
3. **Fixed-weight baseline.** Equal-weight sum of the standardized component logits, with weights pre-registered. Used in the ablation.
4. **Calibration.** Platt scaling on the out-of-fold stacker outputs, nested inside the same CV.
5. **Pre-registration** (`eval/seal.py`). Before the first run of `scripts/06_replay.py`:
   - Write `configs/preregistration.lock` containing the SHA-256 of all configs, `peers.csv`, `harmonized_map.yaml`, the nbfc weights, the policy params, and the code tree hash.
   - Replay and evaluation verify the lock and abort if it doesn't match, unless `--amend "<reason>"` is passed. Amendments are logged to `outputs/amendments.log` and shown in the report. **This log is a feature, not an embarrassment.**

---

## Phase 5 (P0): historical replay, metrics, policy (deliverables 2 and 5)

1. **`eval/replay.py`.** For each quarter-end *t* in FY2014–FY2024:
   - build features
   - score PD_4q and PD_8q (out-of-fold)
   - build the watch-list with `policy/watchlist.py`
   - persist `outputs/replay/<t>.parquet`, containing rank, tier, PD, attributions and flags
2. **`policy/watchlist.py`.**
   - K_t = floor(0.05·N_t).
   - Hard-trigger names go first, then names sorted by PD (× EAD if provided).
   - Tier assignment follows PROJECT_IDEA §6.
   - Names ranked K+1…M with PD ≥ τ\* are tagged `containment`.
   - `assert len(deep_review) <= K_t`.
3. **`policy/cost.py`.**
   - Expected cost per quarter: Σ_{not flagged} 20p + Σ_{flagged} (1−p).
   - Realised cost: 20·FN + FP against `y_4q`.
   - Cost curve over K = 0…2K_t.
   - Empirical τ scan.
   - Shadow price = Δ expected cost from K to K+1…K+20.
4. **`eval/metrics.py` (India).** Each recall below also gets a Wilson 95% CI.
   - **Recall@5% at event−4Q and at event−8Q.** This is the primary, strict single-date metric.
   - **"Ever flagged" in [event−8Q, event−4Q].**
   - Median first-flag lead time.
   - Precision of the watch-list.
   - **False-alarm rate**, overall and among stressed survivors.
   - Watch-list turnover.
   - All of the above under the alternative event definition (the CIRP admission date).
5. **`eval/ablation.py`.** Recall@5% (4Q and 8Q) and realised cost for these variants:
   - HDM only
   - +forensic
   - +CHS
   - +soft
   - full stacker
   - fixed-weight baseline
   - Altman-only and CHS-only baselines
6. **Case cards** (`eval/report.py`). One card per defaulter: the PD path, rank vs K_t, the first-flag quarter, the dominant pillar at the first flag, and the dated evidence (filings, ratings, auditor exits, pledge). Misses are explained honestly, for example "accounting benign; market signal only at −3Q".

**Acceptance**
- `outputs/india_metrics.csv`, `outputs/ablation.csv`, `outputs/cost_curve.png` and `outputs/case_cards/*.md` exist.
- `tests/test_policy.py` asserts the cap holds for every quarter and checks that τ\* = 1/21 to 4 decimal places.

---

## Phase 6 (P0): explainability (deliverable 4)

1. **`explain/attribution.py`.**
   - The final logit = intercept + Σ w_j·c_j, so the contribution of component j is w_j·c_j.
   - For the HDM, split w_hdm·hdm_logit across features using TreeSHAP values on the margin (`shap.TreeExplainer(model, model_output="raw")`). Scale the expected-value term into the intercept.
   - CHS is split linearly using its coefficients.
   - Assert that the attributions sum to the final logit to within 1e-6.
   - Convert to PD percentage points for display: the change in PD from removing each driver, holding the others fixed (marginal at the current logit).
2. **`explain/pillars.py`.** Map every feature to one of the 5 pillars in `configs/pillars.yaml` and sum within each pillar.
3. **`explain/templates.py`.** Deterministic Jinja-style templates, one per feature, each with a `concern` and an `action`. Placeholders: {value}, {sector_median}, {pctile}, {delta_4q}, {pd_pts}. Write at least 25 templates covering every model input. Text must not depend on anything except these values.
4. **`explain/archetype.py`.** Normalize the attribution vectors. For each flagged firm, find the nearest defaulter's attribution vector from its first-flag quarter (excluding itself and its own case group), and output the archetype name and distance. Optional, P2: a minimum-spanning-tree plot of the flagged firms.
5. **Memo output.** One markdown/HTML memo per flagged firm per quarter: header (rank, tier, PD_4q, PD_8q, hard triggers), the top 3 drivers, pillar bars, archetype, and SLA actions.

---

## Phase 7 (P1): Streamlit app (`app/streamlit_app.py`)
The app only reads files from `outputs/`; nothing is recomputed live. This keeps it fast and reproducible. It has four tabs:
1. **Time Machine.** Quarter slider; a 40-row table with rank, name, sector, tier, PD, top driver and a hard-trigger icon. A "Reveal outcomes" checkbox colours names that later defaulted within 4Q/8Q.
2. **Case Timeline.** Plotly line of PD and rank-percentile over time, with event markers (filings, rating actions, auditor exits, pledge), and lines for τ\* and the top-5% cut-off.
3. **Borrower Memo.** The rendered memo with a download button.
4. **Policy & Metrics.** Benchmark table, India recall table with CIs, cost curve, shadow price, ablation chart, calibration plot, coverage-parity table and amendments log.

## Phase 8 (P0): report and pitch
- `scripts/09_build_report.py` fills `report/final_report.md` from the outputs.
- **Report sections:** problem → data and point-in-time design → benchmark → Indian panel → forensic/soft signals → policy and cost math (with the worked numbers) → explainability examples (IL&FS/ITNL, DHFL, Jet) → limitations (PROJECT_IDEA §9) → reproducibility (commands and lock hash).
- **Slides outline** (10 slides): the IL&FS hook → the "time machine" demo → leakage proof → the 5%-budget proof → cost math → case cards → ablation → limitations → ask.

## Phase 9 (P2): extras if time allows
- EAD-weighted ranking using synthetic exposures, labelled as such.
- Watch-list hysteresis with a turnover vs recall trade-off chart.
- PSI drift monitor page.
- Policy simulator: K = 20/40/60 and cost ratios 10/20/50, with resulting recall and cost.

---

## Phase 10: signature features (spec in PROJECT_IDEA §8c)
1. **(P0) `explain/provenance.py`.**
   - For a firm and two consecutive scoring dates, list the source rows with `t_prev ≤ public_date < t`, sorted by date.
   - Re-score cumulatively, adding one item at a time, and record ΔPD with the document type, date and `source_url`.
   - Store the result as `outputs/provenance/<entity>.parquet`. The memo shows the document that pushed the firm over τ\* or into the top K.
   - **Test:** the ΔPDs telescope, so their sum equals PD(t) − PD(t_prev).
2. **(P0) `eval/detection_curve.py`.**
   - For lead L from 12 down to 0, compute the share of defaulters on the watch-list at event − L. Do this for PRAHARI, the rating-sub-IG baseline (from `rating_actions.csv`) and the Altman-distress-zone baseline.
   - Compute the median of (first sub-IG rating date − first PRAHARI flag date) in quarters.
   - Produce the hero chart for the report, the app and slide 2.
3. **(P1) `features/group.py` plus `data/manual/groups.csv`.**
   - `groups.csv` columns: `entity_id`, `group_name`, `source_url`.
   - **`group_stress(i,t)`:** the maximum over siblings j ≠ i of {a hard trigger, a default, or a top-decile PD}, using as-of data only.
   - Add it to the soft overlay with a +0.8 log-odds weight, pre-registered.
   - In `eval/metrics.py`, add group-clustered recall.
4. **(P1) `eval/anti_gaming.py`.**
   - Apply the three perturbations in §8c.4 to the raw financials of every Tier-1/2 firm.
   - Rebuild its features and re-score.
   - Report ΔPD. Fail with a warning if the relative drop exceeds 10%.
   - Output `outputs/anti_gaming.csv` plus a chart.
5. **(P0) Sealed cases.**
   - Store the sealed cases in `data/manual/sealed/`; this folder is git-ignored until the final run. `seal.py --final-sealed` scores them once and logs the run.
   - **App:** add a "Judge's pick" box (entity + quarter → replay, memo and evidence chain), an "Evidence chain" panel on the Memo tab, and the detection curve on the Metrics tab.
6. **(P1) Report.** Add an appendix mapping each tier to the RBI EWS/RFA workflow steps, with a template for a Tier-1 EWS trigger note.

## Commands (end-to-end)
```
pip install -r requirements.txt
python scripts/01_benchmark.py          # Phase 1 → outputs/benchmark_metrics.csv
python scripts/02_market_data.py        # bhavcopy + index cache
python scripts/03_validate_manual.py    # schemas, identities, coverage parity
python scripts/04_build_universe.py
python scripts/05_build_features.py     # per-quarter feature parquet
python scripts/05b_seal.py              # writes preregistration.lock
python scripts/06_replay.py             # OOF stacker, watch-lists, memos
python scripts/07_evaluate.py           # India metrics, ablation, cost curve, case cards
python scripts/09_build_report.py
pytest -q
streamlit run app/streamlit_app.py
```

## Required tests (all P0)
| Test | What it asserts |
|---|---|
| `test_asof.py` | `as_of` never returns rows with `public_date ≥ t`; returns the latest row per field |
| `test_leakage.py` | Features at *t* stay the same after deleting all future rows; `max_source_date < t` |
| `test_no_raw_reads.py` | No module outside `prahari/data/` reads `data/manual` or `data/raw` directly |
| `test_holdout_seal.py` | The benchmark hold-out is used once; transforms are never fit on hold-out indices |
| `test_forensic.py` | Altman, Beneish, Piotroski and CHS match hand-computed toy examples |
| `test_policy.py` | Deep-review size ≤ K_t for every quarter; τ\* = 1/21; correct tier logic |
| `test_attribution.py` | Attributions sum to the final logit (tolerance 1e-6) |
| `test_prereg.py` | Replay aborts if a locked file changes without `--amend` |

## Risk register (what to do when things break)
| Risk | Mitigation |
|---|---|
| Background financials unavailable | Fall back down the ladder in §2.3. At minimum, run a market-only universe and report it transparently. |
| Exact filing dates unknown | Apply the conservative lag rule and flag those rows in the report. |
| A defaulter's data is too sparse | Swap it for another candidate. Keep ≥ 10 cases and log the swap in the amendments log *before* evaluation. |
| The stacker overfits | The fixed-weight baseline is pre-registered. Report both and lead with whichever was pre-declared as primary (the stacker, unless amended). |
| Bhavcopy URL format changes by year | Implement per-era URL builders. Cache everything. Use the BSE bhavcopy as fallback. |
