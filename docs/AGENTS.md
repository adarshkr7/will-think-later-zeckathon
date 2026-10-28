# AGENTS.md: operating rules for the coding agent (Codex)

You are building **PRAHARI**, a submission for Zeckathon PS-02 (Risk & Fraud). Read these in order:
1. `docs/ps.pdf`: the problem statement and judging criteria.
2. `docs/PROJECT_IDEA.md`: what we are building and why.
3. `docs/IMPLEMENTATION_PLAN.md`: phases, modules, tests and acceptance checks.
4. `docs/gemini_report.txt`: the literature background. Use it for formulas only, after checking them against this file and the plan.

**Precedence when documents conflict:**
- §8b and §8c of `PROJECT_IDEA.md` override earlier sections.
- The OVERRIDE note in Phase 4 of `IMPLEMENTATION_PLAN.md` overrides the stacker steps below it.
- This file overrides both on *how* to work.

---

## 1. Non-negotiable rules (breaking any of these loses the hackathon)

1. **Never fabricate real-world data.** Do not invent financial values, event dates, rating actions, pledge percentages, URLs or group memberships for real companies. Do not fill them from memory or from an LLM either.
   - If a value is unknown, leave it empty and set `needs_verification=1`.
   - Then add an entry to `DATA_REQUESTS.md` (see §4).
2. **Synthetic data lives only in `tests/fixtures/`.** Every synthetic row has `is_synthetic=1`. A test must fail if any synthetic row reaches `data/processed/`, `outputs/` or the app.
3. **No look-ahead.** Indian data is read only through `prahari.data.asof.as_of(table, t)`.
   - Every row has a `public_date`. When the true date is unknown, use the conservative lag rule (FY-end + 90 days for results, + 180 days for annual-report-only fields) and set `date_is_imputed=1`.
   - Preprocessing is fit only on training folds, or on the cross-section at date *t*.
4. **Indian labels never train the primary model.** They are used only in `eval/` and in the ablation-only stacker, whose predictions are all out-of-fold.
5. **Do not touch sealed data.**
   - Never open, print or log anything in `data/manual/sealed/` or the benchmark hold-out indices, except through `seal.py --final` or `seal.py --final-sealed`.
   - Never tune anything after seeing hold-out or sealed results. If you must change a locked file, run with `--amend "<reason>"`. The amendment log is shown to the judges.
6. **Every number in the report or app comes from `outputs/`.** Do not hand-type metrics into markdown, slides or the UI. `scripts/09_build_report.py` fills them in.
7. **The 5% cap is hard.** The deep-review list must never exceed `floor(0.05·N_t)`. Constants live in `configs/policy.yaml` (`cost_fn: 20`, `cost_fp: 1`, `alert_frac: 0.05`) and are never written as literals in code.
8. **Report results honestly.** Report misses, wide confidence intervals and failed anti-gaming checks exactly as they come out. Never tweak a threshold, an event-date definition or the peer list to make a case "hit".

## 2. Environment (the user is on Windows 11)

- Use **Python 3.11** in a venv at `.venv`. Write code that runs on PowerShell: use `pathlib`, avoid bash-only scripts, and avoid `make`.
- Provide `run_all.ps1`, which runs the pipeline end to end, and `run_tests.ps1`. Every script under `scripts/` must also work with `python -m scripts.<name>`.
- Read every setting, including file paths, from `configs/*.yaml`. Never hard-code absolute paths.
- **Seeds:** use the single global seed from `configs/base.yaml`. Set the LightGBM option `deterministic=True`.
- **Git:**
  - Run `git init` if needed.
  - Commit after each phase with a message of the form `phase N: <summary>`.
  - Commit `configs/preregistration.lock` **in its own commit, before** the first replay.
  - Never commit `data/raw/`, `data/manual/sealed/`, `.venv/`, or credentials and cookies.

## 3. Web and data etiquette

- **Caching.** Cache every download under `data/raw/<source>/` and never download the same file twice; scripts must be idempotent.
- **NSE/BSE requests.**
  - Use a `requests.Session` with browser-like headers and keep it at 1 request per 2–3 seconds or slower.
  - Retry with exponential backoff, at most 5 attempts.
  - If you're blocked (HTTP 401, 403 or 429 repeatedly), **stop**. Log the failure and add a `DATA_REQUESTS.md` entry asking the human to download the file manually and saying where to put it.
- **Logged-in sites.** Read cookies or session data for sites such as Screener only from environment variables (`SCREENER_SESSION`). Never write them to disk or logs.
- **Provenance.** Every row of hand-collected or scraped data stores its `source_url` or `source_doc`.

## 4. Human-in-the-loop files (create and keep these up to date)

- **`DATA_REQUESTS.md`.** A checklist of data only humans can provide, ordered by priority. Each item gives the company, the field, the period, the suggested source (IBBI, NCLT order, CRA press release, BSE announcement, annual report page) and the target CSV with its column names.
  - Keep a running count at the top, for example "events verified: 7/12, peers: 20/36".
- **`PROGRESS.md`.**
  - Phase status (`todo` / `doing` / `done`) with the acceptance checks passed.
  - The latest `pytest` summary.
  - Open risks.
  - The next 3 actions.

  Update it at the end of every working session.
- **`DECISIONS.md`.** A one-line log of every judgement call: choice, alternative considered, and reason. Judges may ask about any of these choices, and this file is our answer.

## 5. Build order and scope control

1. **The MVP comes first, in this order:**
   1. Phase 1 (benchmark).
   2. Phase 2 (panel only).
   3. Phase 3.
   4. Phase 4 (the zero-Indian-label primary model).
   5. Phase 5 (Arena P).
   6. Phase 6.
   7. Phase 10 items 1, 2 and 5.
   8. Phase 7 (app).
   9. Phase 8 (report).
2. **Arena U (the ~800-firm universe) is built in parallel** and never blocks the MVP. If the financial data is late, use the market-only fallback and record that in `DECISIONS.md`.
3. **Wait on P1/P2 work** until every P0 acceptance check passes and `pytest` is green.
4. **Keep a demoable state at all times.** After Phase 6, `outputs/` must always contain a complete, consistent set of results, so the app works even if later phases are unfinished.

## 6. Code standards

- **Style.** Use type hints and small pure functions. Feature functions take a DataFrame from `as_of` and return a DataFrame keyed by `entity_id`, with a `max_source_date` column.
- **Logging.** Use the `logging` module, not prints. Each script logs row counts, how many dates were imputed, and which features are missing.
- **Fail loudly.** If a formula's input is missing, return NaN with a reason column; never default it to 0. Guard every division.
- **Formulas.** Every formula (Altman Z, Altman Z'', Beneish M, Piotroski F, Hillegeist, CHS, prior shift, τ\*) gets a docstring with its citation and a unit test against a hand-computed example.
- **App.** `app/` only reads files from `outputs/`; it never computes live. A cold start must take under 5 seconds.
- **Explanation text.** Memo and explanation text comes only from the deterministic templates in `explain/templates.py`. No LLM calls anywhere in the pipeline.

## 7. Definition of done (the whole project)

- [ ] `run_all.ps1` runs end to end from cached data with no manual steps.
- [ ] `pytest` is green, including the leakage, policy, attribution, pre-registration, synthetic-data-firewall and telescoping-provenance tests.
- [ ] `outputs/` contains:
  - [ ] benchmark metrics (PR-AUC with CIs and base rates)
  - [ ] India Recall@5% at 4Q and 8Q for Arena U and Arena P, with Wilson CIs, by period, by sector and group-clustered
  - [ ] the cost curve with τ\* and the shadow price
  - [ ] the ablation results
  - [ ] the detection curve against ratings
  - [ ] the placebo test
  - [ ] the anti-gaming table
  - [ ] case cards for **every** defaulter, hits and misses alike
  - [ ] memos with evidence chains
- [ ] `report/final_report.md` is generated, and every number in it traces back to a file in `outputs/`.
- [ ] Each of the app's four tabs, plus the "Judge's pick" box, works offline.
- [ ] `configs/preregistration.lock` is committed before the replay, and `outputs/amendments.log` is included in the report.
- [ ] The sealed cases have been scored exactly once.
- [ ] `PROGRESS.md`, `DECISIONS.md` and `DATA_REQUESTS.md` are current.

## 8. When unsure

Pick the option that is **more conservative about leakage**: later dates, harsher event definitions, fewer features. Record the choice in `DECISIONS.md` and keep going. Ask the human only for things listed in `DATA_REQUESTS.md`. Don't stop for questions about style or structure.
