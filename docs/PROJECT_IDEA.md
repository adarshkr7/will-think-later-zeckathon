# PRAHARI: a point-in-time early-warning system for Indian corporate credit

> **PRAHARI** (Hindi for *sentinel*) stands for **P**oint-in-time **R**isk & **A**ccounting **H**azard **A**lerts, **R**anked & **I**nterpretable.
> Zeckathon PS-02 (Risk & Fraud): an early-warning system that would have caught IL&FS.

---

## 1. One-line pitch

**A "credit-desk time machine".** Pick any past quarter, say Q2 FY2018. PRAHARI rebuilds what the market and the filings showed on that date, using only documents that had been published by then. It ranks 800 indebted listed borrowers and hands the desk a 40-name watch-list. Each name comes with a three-line credit memo written as a credit officer would write it. We then fast-forward and check which later defaulters were already on the list 4 and 8 quarters before they defaulted.

Judges will cross-examine three things: *could you really have flagged it then*, *is the 5% budget respected*, and *does the threshold minimise 20·FN + FP*. Each of those is a built-in, testable property of the system, not something we argue for afterwards.

---

## 2. Why this wins (differentiators)

| # | Differentiator | Why judges care |
|---|---|---|
| 1 | **As-of-date engine.** Every feature value carries a `public_date` (the date it was disseminated on the exchange or by the rating agency). Scoring at date *t* joins only rows with `public_date < t`. A unit test fails the build if any feature row is dated after *t*. | Leakage is ruled out by construction and proved by a test. |
| 2 | **Pre-registration (sealed evaluation).** Model configs, weights and the list of peers are frozen. Their SHA-256 hash is committed **before** the Indian labels are first read. The evaluation script refuses to run if the hash changed after the labels were opened. | Shows we didn't tune on IL&FS or DHFL after seeing the answers. |
| 3 | **Realistic universe, not a toy panel.** About 800 indebted listed firms are scored every quarter. The universe is rebuilt point-in-time from historical bhavcopy listings, so firms that later delisted are included. This avoids survivorship bias. Recall@5% is measured against this universe. | On a panel of only 40 firms, "top 5%" means 2 names, so the metric would be meaningless. Most teams will fall into this trap. |
| 4 | **Exact end-to-end explanations.** Every component of the final model is additive in log-odds: TreeSHAP on the margin, plus linear CHS, plus a linear stacker. Attributions therefore add up **exactly** to the final score. They are grouped into 5 credit pillars and written up with deterministic templates. No LLM is involved, so nothing can be hallucinated. | Explanations are auditable and reproducible. |
| 5 | **Cost-optimal policy under a hard capacity cap.** The calibrated PD gives the Bayes threshold τ\* = 1/21. The desk works `min(40, #{p ≥ τ*})` names. We report the **shadow price of capacity**, i.e. the expected loss avoided by a 41st review slot. | Answers the 20:1 cost requirement and the 5% budget at the same time, with the arithmetic shown. |
| 6 | **Separate track for financial firms.** IL&FS, DHFL, Reliance Capital and Srei are lenders. Altman, Beneish and the Polish ratios do not apply to them, so financials get their own scorecard (ALM, CP dependence, GNPA, capital adequacy, leverage). | Closes the most obvious loophole: running Altman Z on an NBFC. |
| 7 | **Honest coverage boundary.** For each case we publish the *first quarter it was flagged* and which pillar fired. We also say plainly when accounting data alone was blind: DHFL's filings looked benign until market and ALM signals showed up. | Admitting limits is part of the judging rubric ("limits of historical case reconstruction"). |
| 8 | **Ablation ladder.** We report how much each layer adds: benchmark model only → +forensic scores → +CHS market hazard → +soft signals. | Shows that every component contributes. |

---

## 3. System architecture

```
                ┌──────────────────── DATA LAYER (all rows carry public_date) ────────────────────┐
 UCI Polish ──► │ Benchmark store      Annual financials (std + consol)   Market (NSE/BSE bhavcopy) │
 UCI Taiwan ──► │                      Shareholding/pledge (quarterly)    Rating actions (CRA PRs)  │
                │                      Auditor exits / CARO / delayed filings   Events (IBBI, CRA 'D')│
                └──────────────────────────────────────┬───────────────────────────────────────────┘
                                                       │  as_of(t) join  (public_date < t)
                                                       ▼
        ┌────────────── LAYER A ──────────────┐  ┌──── LAYER B ────┐  ┌──── LAYER C ────┐  ┌──── LAYER D ────┐
        │ Harmonized Distress Model (HDM)     │  │ Forensic scores │  │ CHS market      │  │ Soft signals    │
        │ LightGBM, monotone constraints,     │  │ Altman Z''(EM), │  │ hazard (fixed   │  │ pledge lvl/Δ4Q, │
        │ trained on UCI Polish (1y & 2y      │  │ Beneish M (8v), │  │ published coefs)│  │ auditor exit,   │
        │ horizons) on ratios computable from │  │ Piotroski F,    │  │ NIMTAAVG, TLMTA,│  │ rating Δ/watch/ │
        │ Indian filings; rank-transformed;   │  │ Hillegeist Z,   │  │ EXRETAVG, SIGMA,│  │ INC, delayed    │
        │ calibrated + prior-shift corrected  │  │ cash-conv. gap  │  │ CASHMTA, ...    │  │ filing, CARO/GC │
        └──────────────────┬──────────────────┘  └───────┬─────────┘  └───────┬─────────┘  └───────┬─────────┘
                           │  (Financials track replaces A+B with NBFC scorecard: ALM, CP share, GNPA, CAR, D/E)
                           └──────────────┬────────────────┴─────────────────────┴────────────────────┘
                                          ▼
                    LAYER E: sparse logistic stacker (≤ 8 inputs, sign-constrained, L2),
                    fit with leave-one-case-group-out CV → calibrated PD_4Q and PD_8Q
                                          ▼
                    POLICY: rank by PD (× EAD if supplied) → Tier 1/2/3 within K = 40,
                    hard-trigger escalation, containment rules for names 41..M above τ*
                                          ▼
                    EXPLAIN: exact log-odds attribution → 5 pillars → top-3 drivers →
                    credit memo (value, peer-median percentile, 4Q trend, concern, action)
                    + nearest historical failure archetype (SHAP-vector nearest neighbour)
```

### 3.1 Layer A: the Harmonized Distress Model (deliverable 1, reused on Indian data)
- **Benchmark (deliverable 1).** We train full-feature LightGBM models on UCI Polish `4year.arff` (about a 1-year horizon, i.e. 4Q) and `3year.arff` (about 2 years, i.e. 8Q). We also train one on UCI Taiwan.
  - **Untouched hold-out.** A stratified 20% hold-out is set aside first. Its row indices are hashed and stored, and it is opened exactly once.
  - **Leakage-free tuning.** Tuning uses nested 5-fold CV. Imputation, winsorization and correlation pruning (|r| > 0.8) are fit inside each fold only. Missing values also get explicit missingness flags.
  - **Imbalance handling.** We compare `scale_pos_weight` against SMOTE applied inside folds only, and report both. Isotonic calibration is fit on out-of-fold predictions.
  - **Reported metrics.** PR-AUC with a bootstrap 95% CI and the base rate stated, ROC-AUC, Brier score, ECE, and Recall@5%.
- **Is the split "genuinely out-of-sample"?** The Polish data has no timestamps per row, and we say so openly. To get a split that is truly out-of-sample, we add a **cross-country transfer test**: a model trained on harmonized Polish ratios is scored on harmonized Taiwan ratios. This is a different country, period and data vendor, and we report its PR-AUC.
- **Harmonized model.** We use only the 12–15 ratios that can be computed from Indian annual reports: ROA, TL/TA, WC/TA, current ratio, quick ratio, RE/TA, EBIT/TA, equity/TL, sales/TA, (GP+Dep)/TL, ST-liabilities/TA, sales growth, and so on.
  - **Rank transform.** Each ratio is converted to a percentile rank within its cross-section. This removes differences in currency, accounting regime and scale.
  - **Monotone constraints.** For example, a higher TL/TA can never lower risk. This makes the model transfer better and keeps its explanations sensible.
  - **Prior-shift correction.** PDs are rescaled from the Polish base rate (about 5%) to the Indian universe base rate using the Saerens–Elkan prior-shift formula.

### 3.2 Layer B: forensic screen (deliverable 3)
- **Altman Z''** (emerging-market, non-manufacturing variant) and the classic Z for manufacturers. We also include the Hillegeist "updated Z" logit.
- **Beneish M.** All 8 variables, with the M > −1.78 flag, plus TATA and DSRI as standalone features.
- **Piotroski F** on its 9-point scale (F ≤ 3 counts as weak).
- **Cash-conversion gap** = (PAT − CFO)/TA.
- **Consolidated-to-standalone debt multiplier**, the IL&FS signature.
- **Financials track.** These scores are not computed for NBFCs/HFCs; we mark them N/A rather than produce misleading numbers.

### 3.3 Layer C: CHS market hazard
These are the Campbell–Hilscher–Szilagyi (2008) variables, computed from NSE/BSE bhavcopy prices and shares outstanding: NIMTAAVG, TLMTA, CASHMTA, EXRETAVG (vs Nifty 500), SIGMA, RELSIZE, MB and PRICE. We use the **published coefficients as-is**, so nothing in this layer is fitted to Indian defaults. This is the layer that catches DHFL in Sep 2018, when its accounting still looked clean.

### 3.4 Layer D: soft signals (≥ 2 required; we ship 5)
1. **Promoter pledge.** Pledge % and its 4-quarter change, plus the interaction term pledge × TLMTA × max(0, −NIMTAAVG).
2. **Mid-term auditor resignation.** Taken from Reg 30 disclosures (dated by exchange announcement).
3. **Credit-rating actions.** Notch change over 4 quarters, Watch-Negative / Negative outlook, "Issuer Not Cooperating" (INC), and CP-limit cuts. Each is dated by the press release.
4. **Delayed statutory filing.** A flag set when results are not filed within the LODR window (45 days for quarterly results, 60 days for annual).
5. **Audit-report red flags.** CARO default/fraud clauses, going-concern or qualified opinion. These are dated by the annual-report filing date.

Related-party loans relative to net worth are an optional sixth signal, collected for the matched panel.

### 3.5 Layer E: the stacker
A logistic regression with at most 8 inputs: HDM logit, CHS score, Z'', M, F, a pledge composite, a rating composite and a governance-flag count.
- **Sign constraints.** Every input is forced to push risk in its economically sensible direction.
- **Grouped CV.** It is fit with **leave-one-case-group-out CV**, where a group is one defaulter plus its matched peers. Every Indian prediction we report is therefore out-of-fold.
- **Ablation baseline.** As an alternative that needs no training on Indian data, Layers A+B+C+D are combined with pre-registered fixed weights. This version is reported in the ablation table.

---

## 4. Indian case panel (deliverable 2)

- **Defaulters.** We target **≥ 12** (the requirement is 10), spread across sectors. The candidate list below is indicative; every event date must be sourced and verified before we freeze.
  - **IL&FS group.** IL&FS Transportation Networks (ITNL) is the listed proxy. The IL&FS parent is unlisted, which we state explicitly. It is shown separately in accounting-only mode, using its public annual reports.
  - **Non-financial and financial cases:** DHFL, Jet Airways, Reliance Capital, Reliance Home Finance, Future Retail, Coffee Day Enterprises, Reliance Communications, Srei Infrastructure Finance, Videocon Industries, Jaypee Infratech, Alok Industries, Amtek Auto, Bhushan Steel, Lanco Infratech, Sintex Industries and Cox & Kings.
- **Event-date rule.** The event date is the **earliest** of three: the first publicly disclosed debt-servicing default, the first 'D' rating from any CRA, or the date NCLT admitted the CIRP. Each date is recorded with a source URL.
  - Taking the earliest date gives the shortest possible lead time, which is the conservative choice. We report results under the CIRP-admission date as well.
- **Peers.** At least 3 per defaulter, so **≥ 36** in total. They come from the same sector and are the closest by total assets at event − 12Q.
  - At least a third must be **"stressed survivors"** (hard negatives): leverage in the top quartile of the sector, with no default within 8 quarters. Examples to verify: Indiabulls Housing, PNB Housing and Vodafone Idea.
  - Peers are chosen by a script, using rules frozen before scoring begins.
- **Data symmetry rule (anti-loophole).** Every feature is collected with the **same procedure** for defaulters and peers.
  - **Panel features.** A feature may enter the full-universe model only if a *coverage-parity test* passes. This test checks that missingness rates do not differ between defaulters and non-defaulters because of how the data was collected. Features that fail run in panel mode only.
  - **Background firms.** If a background firm later defaulted but is not in our panel, we cross-check it against the IBBI CIRP list of listed companies and label it correctly. Any defaulter we cannot verify is counted as a false positive if flagged. This is the conservative choice.

---

## 5. Evaluation protocol (maps 1:1 to PS-02 metrics)

| PS metric | Our exact definition |
|---|---|
| Recall of Indian defaulters at a 5% alert rate, 4Q and 8Q | At the scoring quarter-end *t = event − 4Q* (and *− 8Q*), is the defaulter in the top ⌊0.05·N_t⌋ of the universe of N_t ≈ 800 firms? This strict single-date version is our **primary** metric. We also report "flagged at least once in the window [event−8Q, event−4Q]" and the median first-flag lead time. |
| PR-AUC on benchmark hold-out | Untouched 20% hold-out for Polish 4year/3year and Taiwan, each with its base rate stated (≈ 5.3%, ≈ 4.7%, 3.23%) and a bootstrap CI. We also report the cross-country transfer PR-AUC. |
| Expected loss (FN = 20 × FP) | Expected-cost formula and empirical cost per quarter, both written out in §6 below. Cost curve over K = 0…80 with τ\* and K = 40 marked. Realised totals of 20·FN + FP from the historical replay. |
| Leakage control | `as_of` join, a CI test asserting max(public_date) < t for every scored row, sealed pre-registration hash, and preprocessing fitted only on data with dates < t. |

The expected-loss row uses these two formulas. Expected cost under policy S:

`E[cost] = Σ_{i∉S} 20·p_i + Σ_{i∈S} (1 − p_i)`

Empirical cost per quarter:

`20·FN + FP`

**Other reported items:** calibration curve, watch-list turnover between quarters, false-alarm rate among stressed survivors, a per-pillar ablation table, and a per-case timeline card for every defaulter (hits *and* misses).

---

## 6. Operating policy (deliverable 5)

1. **Threshold.** The threshold is τ\* = C_FP/(C_FP + C_FN) = 1/21 ≈ 0.0476 on calibrated PD_4Q. Flagging firm *i* lowers expected cost exactly when p_i ≥ τ\*. We also check τ\* empirically: on held-out data we scan τ from 0.01 to 0.5 and show the cost-minimising value sits near 1/21.
2. **Quarterly ranking.** About 30 days after quarter-end (once most results are filed), all N borrowers are ranked by expected-loss score `S_i = PD_i × EAD_i × LGD`. If exposure data is missing, EAD defaults to 1, which makes this a ranking by PD.
3. **Capacity rule.** M is the number of names with PD ≥ τ\*.
   - **If M ≤ 40:** all M go to deep review. The leftover slots go to the next-highest names as Tier 3 preventive monitoring.
   - **If M > 40:** the top 40 get deep review. Names 41…M trigger automatic containment that takes no analyst time: freeze incremental limits, refuse CP/ST rollovers, request a statutory auditor query. They are first in line next quarter.
   - **Hard cap.** The deep-review list is **never more than 40 names**. A test asserts this for every quarter.
4. **Hard triggers.** A mid-term auditor resignation, a rating of INC or 'D', or a going-concern opinion moves a firm to the top of the queue. It still uses one of the 40 slots.
5. **Tiers and SLAs.**
   - **Tier 1** (PD ≥ 0.15 or a hard trigger): credit committee within 5 working days, CP rollover freeze, forensic review of related-party receivables.
   - **Tier 2** (τ\* ≤ PD < 0.15): senior-analyst deep dive within 15 days, cash-flow stress test, check of pledge covenants.
   - **Tier 3** (filler slots): RM review within 30 days, receivables ageing, covenant watch.
6. **Escalation path.** Analyst → Credit risk head → Credit committee → Board risk committee if exposure exceeds a set limit. An analyst may clear a name, which must be written into a feedback log. Cleared names are re-ranked next quarter and feed the monitoring of model drift.
7. **Shadow price of capacity.** We report the expected loss avoided by review slots 41–60. This gives management a rupee figure to weigh against hiring one more analyst.
8. **Governance.** Recalibrate yearly. Track drift using PSI on the main features and stability of the cost-optimal threshold. Back-test against realised defaults every quarter.

---

## 7. Explainability (deliverable 4)

- **Attributions.** The final logit is the sum of the stacker weights times the component logits. The HDM component is split further using TreeSHAP on its margin. Because everything is in log-odds, all attributions add up exactly to the final score.
- **Pillars.** Attributions are grouped into five pillars: **Liquidity & ALM**, **Solvency & Group Leverage**, **Earnings Quality / Manipulation**, **Market Hazard**, **Governance & Soft Signals**.
- **Top-3 drivers.** Each of the top 3 drivers is shown with its value, the sector-peer median and percentile, the 4-quarter change, its contribution in PD percentage points, a concern written as a credit officer would phrase it, and a verification action. All text comes from fixed templates.
  - **Example:** *"Consolidated debt is 3.4× standalone debt (sector median 1.2×). Most group borrowing sits outside the listed entity, so its ratios understate group leverage. Action: obtain the SPV-level debt and guarantee schedule."*
- **Archetype match.** Each flagged firm is matched to its nearest historical failure by distance between attribution vectors, for example the IL&FS group-leverage pattern or the Reliance Capital pledge-plus-auditor-exit pattern. The match is shown on the memo.

---

## 8. Demo (what judges see)

A Streamlit app with four tabs:
1. **Time Machine.** A quarter slider runs from FY2014 to FY2023. It shows the 40-name watch-list with tiers, plus a toggle to "reveal outcomes" that marks later defaulters.
2. **Case Timeline.** Pick a defaulter to see its PD path over the 12 quarters before the event. Filing dates, rating actions, auditor exits and pledge spikes are marked on the chart, and the τ\* and top-5% cut-offs are drawn as lines.
3. **Borrower Memo.** The top-3 drivers, pillar bars, archetype match and recommended actions. Exportable to PDF.
4. **Policy & Metrics.** Cost curve, shadow price, Recall@5% at 4Q and 8Q, benchmark PR-AUC, the ablation ladder and a calibration plot.

---

## 8b. Red-team revisions (these override anything above that conflicts)

1. **The primary model uses ZERO Indian labels.** A stacker fit on about 10 Indian defaults would overfit, and a judge can attack it with one question.
   - **Primary model (pre-registered):** `PD = calibrated HDM (Polish-trained) ⊕ CHS (published coefficients) ⊕ soft-signal log-odds overlay (weights fixed in config before replay)`.
   - The Indian panel is used **only to test**. The pitch line is: *"No Indian default was used to train or tune this model."*
   - The stacker becomes a secondary, ablation-only result. If it doesn't beat the primary model out-of-fold, we say so.
2. **Two arenas, so soft-signal data asymmetry can't inflate results.**
   - **Arena U (≈800-firm universe):** only features collected the same way for every firm, namely annual financials, market/CHS data and filing delays. **The headline Recall@5% (4Q and 8Q) comes from this arena.**
   - **Arena P (matched panel of defaulters and peers):** the full feature set, including pledges, ratings and auditor exits. It reports the *incremental lift* from soft signals using hand-collected data, gathered the same way for both groups.
   - This removes any chance that "we collected more data for defaulters" explains the results.
3. **Feasibility is the main risk, not modelling.** The minimum viable path is: benchmark → 12 cases + 36 peers → Arena P replay → memos → app.
   - The 800-firm universe is built **in parallel** and goes down the fallback ladder (§2.3 of the plan) as needed. If the full universe isn't ready, Arena U runs market-only on all traded firms (free bhavcopy data), which still has a real N and is survivorship-free.
   - **Never miss the deadline because of Arena U.**
4. **Defaults cluster in time.** Many happened in the 2017 RBI IBC wave and the 2018–19 NBFC crisis. We report recall **by period** and **by sector** so that one shock doesn't masquerade as skill. We also run a placebo test: shuffle event dates within each firm and show that recall collapses.
5. **Benchmark comparisons.** We compare against naive baselines that judges understand: Altman Z only, rating-downgrade only (what a desk already does), and market-cap drawdown only. **Our claim is that PRAHARI beats "just watch ratings" at a 4Q lead.** This is the most persuasive comparison for a credit audience, since ratings famously lagged at IL&FS.

## 8c. Signature features (what no other team will have)

New pitch: ***"Every alert cites the dated public document that triggered it, and we flag defaulters N quarters before the rating agencies did."***

1. **Alert provenance ("evidence chain").** *(P0. It is cheap because the as-of engine already exists.)*
   - **How it works.** Between two scoring dates, re-score the firm adding each newly public item one at a time, in `public_date` order: a results filing, a rating press release, a pledge disclosure, an auditor-exit announcement, the month's price data. The PD change is attributed to each document.
   - **On the memo:** *"Crossed τ\* on 2018-09-xx. Main trigger: CARE watch-negative press release (+3.1 pp, URL). Contributing: 3-month volatility spike (+1.8 pp)."*
   - **Why it matters.** This answers the judges' key question, *"could it truly have flagged it then?"*, with a specific document, a date and a link instead of a claim.
2. **Detection curve against the rating agencies (the hero chart).**
   - **What it shows.** The share of defaulters on the watch-list at each quarter from −12 to 0 before the event. Three lines are drawn: PRAHARI, "rated below investment grade" (what desks rely on today), and "Altman distress zone".
   - **Headline number:** the median number of quarters PRAHARI flags a defaulter before its first sub-investment-grade rating. Ratings famously lagged at IL&FS, so this is the most persuasive single number for a credit audience.
3. **Promoter-group contagion.** Indian defaults come in groups: Reliance ADAG (RCom, Reliance Capital, Reliance Home Finance), IL&FS (ITNL, IL&FS Engineering), Coffee Day (CDEL, Sical Logistics), Videocon, Jaypee. Verify each membership.
   - **Feature `group_stress`.** The worst distress state among a firm's group siblings that was public before *t*: a sibling's hard trigger, a sibling default, or a sibling in the top decile of PD. The firm itself is excluded.
   - **Avoiding inflated recall.** We also report **group-clustered recall**, where each group counts once, so correlated defaults can't flatter the numbers.
4. **Anti-gaming test.** This PS is about concealment, so we prove that a borrower can't talk its way off the watch-list. We run synthetic window-dressing attacks on real flagged firms:
   - **Accrual inflation:** PAT +30%, CFO unchanged, receivables up.
   - **Debt pushed into SPVs:** standalone debt −40%, consolidated debt unchanged.
   - **Extended CP rollover.**

   The test asserts that PD does not fall by more than 10% relative to the original. Each attack is closed by the cash-conversion gap, Beneish M, the consolidated/standalone multiplier, or the market layer. We publish the before/after table.
5. **Verifiable pre-registration plus sealed-envelope cases.**
   - **Public hash.** At kickoff, the hash in `preregistration.lock` is posted publicly (a GitHub commit, or a message to the organisers), giving it an independent timestamp.
   - **Sealed cases.** 2–3 defaulters are collected by one teammate and **never opened by the modellers**. They are scored once, at the end, in front of the judges.
   - **"Judge's pick."** Any listed firm and any quarter can be replayed live from the universe.
6. **Ready to deploy in an Indian bank.** The tiers and escalation path line up with RBI's Early Warning Signals → Red-Flagged Account workflow (Master Direction on Fraud Risk Management, 2024; verify the clause numbers). The Tier-1 memo is formatted as an EWS trigger note that a bank could file.

## 9. Limitations we state up front (this is how we pass cross-examination)

- **Unlisted IL&FS parent.** It has no market data, so it runs in accounting-only mode and we report it separately.
- **DHFL.** The accounting layer misses it until late. Detection relies on the market and ALM signals, and we show this openly.
- **Ten events is a small sample.** CIs on recall will be wide, so we show Wilson intervals and do not oversell.
- **Polish dataset.** It has no row timestamps, so "time-aware" is replaced by an untouched hold-out plus a cross-country transfer test.
- **Filing dates.** Where the exact dissemination date is unknown, we use a conservative lag: FY-end + 90 days for results fields and FY-end + 180 days for annual-report-only fields.
- **Sector effects.** Handled by the separate financials track, sector-relative ranks and sector-matched peers. Some residual concentration remains, especially among NBFCs in 2018–19.
- **Systemic stress.** In stress periods such as the 2018 NBFC crisis, M > 40. That is exactly what the containment tier and the shadow price are for.
