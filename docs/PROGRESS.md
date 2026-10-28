# Progress

Updated: 2026-10-29. Code implementation and scientific acceptance are tracked separately.

| Phase | Status | Acceptance evidence / remaining gate |
|---|---|---|
| 1 benchmark | doing | Development CV, calibration and transfer artifacts exist. Untouched hold-out not opened; final freeze/evaluation deferred. |
| 2 panel | doing | Human-reviewed event import and receipts complete. Original NSE identity/shareholding imports and reviewed ITNL/DHFL statements added. DHFL passes the core financial-year history check; the rest of the panel, peer selection and coverage gates remain incomplete. |
| 3 features | doing | Dated P/U builders and guarded formulas implemented; all configured P/U quarter caches built, with honest source gaps. Data completeness acceptance not passed. |
| 4 primary | doing | Frozen Polish heads, India-local ranks, fixed overlays, financial-track separation and registration/amendment checks implemented. Independent priors/link remain unavailable. |
| 5 replay/evaluation | doing | Registered replay, hard-cap policy, strict recall/Wilson intervals, separate nested OOF ablations, cost/threshold/shadow and placebo runners implemented. No Indian performance evaluation run. |
| 6 explanations | doing | Calibrated logit reconciliation, pillars, deterministic templates, memo export, archetype helper and telescoping adapters implemented/tested. Real scored memos/chains await accepted data. |
| 10 P0 signatures | doing | Detection baselines, publication-dated paired rating-lead export, evidence chains and once-only sealed evaluator implemented. Sealed data unopened; independent collector hash not supplied. |
| 7 app | doing | Four tabs, judge search, historical cutoff, outcome reveal, memo and evidence panel work against offline exports. Measured checks in outputs/ui_validation.json. Visual inspection blocked by unavailable computer-use runtime. |
| 8 report | doing | Output-driven readiness report and source-hash trace generated under docs/report/. Final scientific results remain unavailable. |
| 9 / other P1-P2 | doing | Dated group overlay, anti-gaming, PSI, hysteresis, policy scenarios and internal EWS workflow implemented/tested. Group overlay remains disabled; registered experiment execution awaits P0 acceptance. |

Latest full pytest run: **128 passed, 0 failed, 0 skipped**. Source: `outputs/test_summary.json`. The prior full P/U readiness rebuild completed its benchmark, universe, feature and test stages but stopped at a cold-render timing check (5.8337 seconds). Feature evidence is now loaded on demand, and the separate offline UI validation passes, including the feature checkbox, four tabs, both arenas and judge search; current measured timing is in `outputs/ui_validation.json`. The report is generated separately. A subsequent P/U source refresh is running with the new reviewed inputs; the existing exported bundle remains demoable. The complete latest wrapper run is not claimed to have passed. Production acceptance remains gated.

The user authorized implementing the remaining modules while public-source collection continues. This does not waive data acceptance, pre-registration or the once-only final boundaries. Benchmark hold-out and independent Indian sealed contents have not been opened. No Indian recall, hit/miss or calibrated-probability claim is made in readiness mode.

Actual collection counts are generated in `outputs/collection_status.csv`; app acceptance timings and checks are in `outputs/ui_validation.json`. Unknown values retain reasons and verification flags. Historical market collection resumed after DNS recovered, then was paused to prioritize a single rate-limited NSE financial-filing collector. The failure and resolution are retained in `outputs/source_failures.csv`. The running feature batch uses its immutable source load; later downloads enter a subsequent rebuild. Missing files are not certified holidays; the full historical requirement is not claimed complete. Original-vintage FX covers every configured quarter; `outputs/fx_coverage.csv` records actual observation and publication dates. Its offline rebuild passed.

Automated recovery now includes original historical NSE filing indexes, exact ISIN/symbol identities, original quarterly shareholding XML, and cached annual-report candidates discovered from public document links. Offline reruns of all three collectors pass. The nine supplied sources are reviewed reproducibly in `docs/SOURCE_REVIEW.md` and `outputs/supplied_source_review.csv`; unsuitable definitions and undated third-party values are excluded from production. Counts of candidate PDFs are kept separate from reviewed statement fields. The pipeline preparation sequence imports dated identities before classifications and source-reviewed statements.

Open risks:

- No matched peers; most core financial histories remain incomplete. DHFL's required three-year core history passes and its observed accounting identities pass, but complete NBFC inputs remain outstanding. Earlier source identity proof helps only where the business profile and matching-date financials are also available. Later comparatives cannot establish earlier availability.
- Quarterly shares and pledges are partly recovered, while earlier coverage, historical regulatory minima, independent horizon priors and complete governance coverage remain missing. Empty event searches cannot establish negative signals. FX collection is complete and removed from the team's outstanding tasks.
- Unknown corporate memberships cannot imply independent group denominators. Case-peer CV components are not ownership groups.
- Market-only membership is an honest fallback, not a debt-ranked complete universe or a calibrated market-only PD model. Raw returns and cached indices are unadjusted price observations, not TRI.
- A stale old-evidence counterfactual can be unscorable. Such provenance remains unavailable; no document effect is fabricated to force reconciliation.
- Retrospective first-flag archetype export is integrated with the evaluator and excludes case-peer components. Real scored examples remain unavailable until registration and data acceptance.
- The latest development benchmark generation has byte-identical metrics to the previous generation. No learning settings changed and no Indian performance evaluation was run. Hold-out and sealed final boundaries remain unopened.
- The once-only sealed path requires an independently hashed full-cohort feature artifact; its schema is documented without inspecting protected files.
- Paired rating lead is descriptive of the observed source history, not proof of the first-ever downgrade. Unknown endpoints remain in the case export and incomplete comparisons are flagged.

Next three actions:

1. Finish and verify the source refresh across every configured P/U quarter, regenerate the offline bundle/report, and push verified checkpoints to main.
2. Continue original-source financial histories and the sector-peer candidate pool, then resume the remaining market intervals; keep docs/DATA_REQUESTS.md current. Codex owns this ordinary collection.
3. Pass the data gate, obtain independent priors/link, freeze scientific inputs and commit the Indian lock alone before any scored replay; leave final evaluations unopened until then.

Latest data review: original ITNL FY2016 and DHFL FY2015–FY2018 standalone evidence was added without replacing earlier observations. DHFL liabilities use an explicit sum of printed liability subtotals; missing components remain unknown. Its ambiguously headed comparative income column is excluded. Later reclassified comparatives retain their later source publication date. Reviewed Alok/Videocon evidence and human event dates are preserved. See docs/intake/ITNL_2016_STATEMENT_REVIEW.md, docs/intake/DHFL_STATEMENT_REVIEW.md, outputs/financial_coverage.csv and outputs/collection_status.csv. The public sealed-input contract is docs/SEALED_INPUT_CONTRACT.md.
