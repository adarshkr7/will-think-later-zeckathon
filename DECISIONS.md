# Decisions

- 2026-10-28: Use the zero-Indian-label primary model in PROJECT_IDEA §8b and the Phase 4 override; reject the earlier primary stacker because the later instructions take precedence.
- 2026-10-28: Correct Polish horizon metadata from the primary UCI documentation: 5year = 4Q, 4year = 8Q, 3year = 12Q; retain the requested 3year/4year benchmark comparisons and add 5year for the actual 4Q head. Source: https://archive.ics.uci.edu/dataset/365/polish+companies+bankruptcy+data . The plan/literature horizon labels are off by one year.
- 2026-10-28: Reserve final benchmark hold-outs and do development on training-only nested CV; reject opening them during implementation because no tuning or locked-code changes are allowed after final evaluation.
- 2026-10-28: Compare unweighted LightGBM, class-weighted LightGBM and logistic regression; exclude production SMOTE because AGENTS.md confines synthetic records to tests/fixtures/. No synthetic benchmark rows are generated.
- 2026-10-28: Use only documented shared ratios for HDM transfer; reject matching similar names with different denominators. Missing mappings remain null. Taiwan normalized ratios support rank comparison, not absolute financial comparison.
- 2026-10-28: Fit empirical rank reference tables inside each training fold; reject ranking the complete Polish dataset before splitting because it exposes validation and hold-out covariate distributions.
- 2026-10-28: Preserve previous periods in as_of, choosing the latest public version per entity/field/period/basis; reject dropping historical FYs because Beneish and Piotroski require lagged observations.
- 2026-10-28: Keep required 20:1 costs and alert fraction exclusively in policy.yaml; final empirical threshold scans are descriptive and never change the registered operating threshold.
- 2026-10-28: Start with benchmark dependencies only and pin their complete resolution; add app dependencies when the MVP reaches the app phase.
- 2026-10-28: For Taiwan transfer, fit an unlabelled Taiwan-training-only rank reference and freeze it with the Polish model; reject applying Polish raw-value cutoffs to normalized Taiwan ratios. No target labels or target hold-out covariates fit this reference. Report this adaptation explicitly.
- 2026-10-28: Use four parallel inner-CV workers with two LightGBM threads each on this 16-core host; retain deterministic training and the full predeclared grid instead of reducing validation to a smoke run.
