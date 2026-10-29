# PRAHARI

Readiness report: production evaluation is incomplete

## Problem and decision design

PRAHARI reconstructs information available before each historical scoring cutoff. The primary model uses Polish-trained distress heads, a published market-risk layer and fixed soft-signal weights. Indian cases are evaluation outcomes, not primary training labels.

## Current execution status

| component | status | reason | is_synthetic |
| --- | --- | --- | --- |
| benchmark | final_evaluated | Development results are not untouched hold-out performance. | 0 |
| panel | incomplete | unique_verified_peers, peers_per_case, stressed_survivors | 0 |
| features | partial_data | Missing inputs remain explicit; existing quarter files do not imply complete coverage. | 0 |
| primary_calibration | incomplete | 4q_independent_prior, 8q_independent_prior, prior_source, financial_track_probability_link | 0 |
| registration | blocked | Pre-registration and accepted panel evidence are required before scored replay. | 0 |
| india_evaluation | not_run | No unregistered performance claims. | 0 |
| sealed_evaluation | not_opened | Once-only final boundary; no sealed contents read for readiness. | 0 |

Source: [run_status](../../outputs/run_status.csv).

## Data and point-in-time design

Source observations carry publication dates, conservative date-imputation flags and document references. Every feature source passes the as-of boundary. Later comparative statements retain the later source report's publication lag. Missing inputs retain explicit reasons.

| item | observed | needs_verification | is_synthetic |
| --- | --- | --- | --- |
| market_sessions | 3166 | 0 | 0 |
| market_observations | 5248967 | 0 | 0 |
| distinct_isins | 3275 | 0 | 0 |
| cached_source_pdfs | 85 | 0 | 0 |
| unavailable_source_pdfs | 1 | 1 | 0 |
| verified_financial_fields | 913 | 0 | 0 |
| financial_entities | 15 | 0 | 0 |
| financial_evidence_rows | 1243 | 0 | 0 |
| verified_financial_evidence_rows | 1232 | 0 | 0 |
| cached_original_report_candidates | 458 | 1 | 0 |
| cached_financial_index_windows | 53 | 0 | 0 |
| financial_index_records | 130478 | 0 | 0 |
| verified_identity_mappings | 85 | 0 | 0 |
| verified_quarterly_share_counts | 15 | 0 | 0 |
| verified_quarterly_shareholding | 14 | 0 | 0 |
| verified_first_listing_certificates | 2 | 0 | 0 |
| sourced_group_memberships | 3 | 0 | 0 |
| complete_group_roster_memberships | 0 | 0 | 0 |
| published_session_count_claims | 20 | 0 | 0 |
| certified_session_census_periods | 13 | 0 | 0 |
| sourced_exchange_calendar_rows | 4749 | 0 | 0 |
| complete_core_financial_histories | 12 | 0 | 0 |
| unselected_research_symbols | 52 | 1 | 0 |
| unselected_research_security_ids | 54 | 1 | 0 |
| unselected_research_pairs | 74 | 1 | 0 |
| verified_survival_candidates | 3 | 0 | 0 |
| verified_survival_pairs | 6 | 0 | 0 |
| verified_panel_events | 12 | 0 | 0 |
| verified_case_isins | 12 | 0 | 0 |
| verified_case_classifications | 12 | 0 | 0 |
| verified_event_components | 24 | 0 | 0 |
| verified_fx_observations | 210 | 0 | 0 |
| quarters_with_verified_fx | 44 | 0 | 0 |
| verified_matched_peers | 0 | 1 | 0 |
| received_peer_claims | 208 | 0 | 0 |
| received_peer_files | 9 | 0 | 0 |
| received_peer_claims_approved_for_model | 0 | 0 | 0 |

Source: [collection_status](../../outputs/collection_status.csv).

| check | observed | required | passed | is_synthetic |
| --- | --- | --- | --- | --- |
| verified_events | 12 | 10 | 1 | 0 |
| case_identity_and_classification | 1 | 1 | 1 | 0 |
| unique_verified_peers | 0 | 30 | 0 | 0 |
| disjoint_cases_peers | 0 | 0 | 1 | 0 |
| peers_per_case | 0 | 1 | 0 | 0 |
| stressed_survivors | 0 | 0 | 0 | 0 |
| panel_market_coverage | 1 | 1 | 1 | 0 |
| financial_year_coverage | 1 | 1 | 1 | 0 |
| accounting_identities | 1 | 1 | 1 | 0 |

Source: [panel_acceptance](../../outputs/panel_acceptance.csv).

### Original-vintage FX coverage

| quarter | available | observation_date | public_date | source_url | needs_verification | is_synthetic |
| --- | --- | --- | --- | --- | --- | --- |
| 2013-06-30 | 1 | 2013-06-21 00:00:00+00:00 | 2013-06-24 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20130624/ | 0 | 0 |
| 2013-09-30 | 1 | 2013-09-20 00:00:00+00:00 | 2013-09-23 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20130923/ | 0 | 0 |
| 2013-12-31 | 1 | 2013-12-27 00:00:00+00:00 | 2013-12-30 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20131230/ | 0 | 0 |
| 2014-03-31 | 1 | 2014-03-21 00:00:00+00:00 | 2014-03-24 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20140324/ | 0 | 0 |
| 2014-06-30 | 1 | 2014-06-20 00:00:00+00:00 | 2014-06-23 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20140623/ | 0 | 0 |
| 2014-09-30 | 1 | 2014-09-26 00:00:00+00:00 | 2014-09-29 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20140929/ | 0 | 0 |
| 2014-12-31 | 1 | 2014-12-24 00:00:00+00:00 | 2014-12-29 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20141229/ | 0 | 0 |
| 2015-03-31 | 1 | 2015-03-27 00:00:00+00:00 | 2015-03-30 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20150330/ | 0 | 0 |
| 2015-06-30 | 1 | 2015-06-26 00:00:00+00:00 | 2015-06-29 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20150629/ | 0 | 0 |
| 2015-09-30 | 1 | 2015-09-25 00:00:00+00:00 | 2015-09-28 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20150928/ | 0 | 0 |
| 2015-12-31 | 1 | 2015-12-24 00:00:00+00:00 | 2015-12-28 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20151228/ | 0 | 0 |
| 2016-03-31 | 1 | 2016-03-25 00:00:00+00:00 | 2016-03-28 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20160328/ | 0 | 0 |
| 2016-06-30 | 1 | 2016-06-24 00:00:00+00:00 | 2016-06-27 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20160627/ | 0 | 0 |
| 2016-09-30 | 1 | 2016-09-23 00:00:00+00:00 | 2016-09-26 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20160926/ | 0 | 0 |
| 2016-12-31 | 1 | 2016-12-23 00:00:00+00:00 | 2016-12-27 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20161227/ | 0 | 0 |
| 2017-03-31 | 1 | 2017-03-24 00:00:00+00:00 | 2017-03-27 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20170327/ | 0 | 0 |
| 2017-06-30 | 1 | 2017-06-23 00:00:00+00:00 | 2017-06-26 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20170626/ | 0 | 0 |
| 2017-09-30 | 1 | 2017-09-22 00:00:00+00:00 | 2017-09-25 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20170925/ | 0 | 0 |
| 2017-12-31 | 1 | 2017-12-22 00:00:00+00:00 | 2017-12-26 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20171226/ | 0 | 0 |
| 2018-03-31 | 1 | 2018-03-23 00:00:00+00:00 | 2018-03-26 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20180326/ | 0 | 0 |
| 2018-06-30 | 1 | 2018-06-22 00:00:00+00:00 | 2018-06-25 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20180625/ | 0 | 0 |
| 2018-09-30 | 1 | 2018-09-21 00:00:00+00:00 | 2018-09-24 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20180924/ | 0 | 0 |
| 2018-12-31 | 1 | 2018-12-21 00:00:00+00:00 | 2018-12-26 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20181226/ | 0 | 0 |
| 2019-03-31 | 1 | 2019-03-22 00:00:00+00:00 | 2019-03-25 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20190325/ | 0 | 0 |
| 2019-06-30 | 1 | 2019-06-21 00:00:00+00:00 | 2019-06-24 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20190624/ | 0 | 0 |
| 2019-09-30 | 1 | 2019-09-20 00:00:00+00:00 | 2019-09-23 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20190923/ | 0 | 0 |
| 2019-12-31 | 1 | 2019-12-27 00:00:00+00:00 | 2019-12-30 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20191230/ | 0 | 0 |
| 2020-03-31 | 1 | 2020-03-27 00:00:00+00:00 | 2020-03-30 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20200330/ | 0 | 0 |
| 2020-06-30 | 1 | 2020-06-26 00:00:00+00:00 | 2020-06-29 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20200629/ | 0 | 0 |
| 2020-09-30 | 1 | 2020-09-25 00:00:00+00:00 | 2020-09-28 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20200928/ | 0 | 0 |
| 2020-12-31 | 1 | 2020-12-23 00:00:00+00:00 | 2020-12-28 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20201228/ | 0 | 0 |
| 2021-03-31 | 1 | 2021-03-26 00:00:00+00:00 | 2021-03-29 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20210329/ | 0 | 0 |
| 2021-06-30 | 1 | 2021-06-25 00:00:00+00:00 | 2021-06-28 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20210628/ | 0 | 0 |
| 2021-09-30 | 1 | 2021-09-24 00:00:00+00:00 | 2021-09-27 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20210927/ | 0 | 0 |
| 2021-12-31 | 1 | 2021-12-23 00:00:00+00:00 | 2021-12-27 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20211227/ | 0 | 0 |
| 2022-03-31 | 1 | 2022-03-25 00:00:00+00:00 | 2022-03-28 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20220328/ | 0 | 0 |
| 2022-06-30 | 1 | 2022-06-24 00:00:00+00:00 | 2022-06-27 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20220627/ | 0 | 0 |
| 2022-09-30 | 1 | 2022-09-23 00:00:00+00:00 | 2022-09-26 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20220926/ | 0 | 0 |
| 2022-12-31 | 1 | 2022-12-23 00:00:00+00:00 | 2022-12-27 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20221227/ | 0 | 0 |
| 2023-03-31 | 1 | 2023-03-24 00:00:00+00:00 | 2023-03-27 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20230327/ | 0 | 0 |
| 2023-06-30 | 1 | 2023-06-23 00:00:00+00:00 | 2023-06-26 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20230626/ | 0 | 0 |
| 2023-09-30 | 1 | 2023-09-22 00:00:00+00:00 | 2023-09-25 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20230925/ | 0 | 0 |
| 2023-12-31 | 1 | 2023-12-22 00:00:00+00:00 | 2023-12-26 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20231226/ | 0 | 0 |
| 2024-03-31 | 1 | 2024-03-22 00:00:00+00:00 | 2024-03-25 00:00:00+00:00 | https://www.federalreserve.gov/releases/h10/20240325/ | 0 | 0 |

Source: [fx_coverage](../../outputs/fx_coverage.csv).

FX comes from original weekly H.10 releases with actual publication dates. Revised current historical series are not substituted. Unreported source observations remain missing.

The panel's current identity/classification catalog is distinct from historical matching-quarter availability. An empty event search does not establish a non-default peer or a negative governance signal.

### Received peer-source audit

Received candidate files are preserved separately and reviewed against original disclosures and historical exchange identities. Current identifiers, later financial years, rounded third-party observations and empty registry searches do not establish historical matching eligibility. Contrary original payment-status evidence is retained; the frozen selection rules are unchanged.

Source: [peer_intake_review](../../outputs/peer_intake_review.csv).

## Benchmark development

The following are nested outer-fold or explicitly marked transfer development results. They are not untouched hold-out estimates. Bootstrap intervals condition on fitted predictions and do not cover model-selection uncertainty or correlated firm histories.

| dataset | representation | variant | horizon_quarters | pr_auc | pr_auc_ci_low | pr_auc_ci_high | base_rate | brier | evaluation_split |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| polish_4year | full | none | 8 | 0.64363 | 0.59925 | 0.68591 | 0.052598 | 0.0275 | nested_outer_oof |
| polish_4year | full | class_weight | 8 | 0.63505 | 0.58931 | 0.68066 | 0.052598 | 0.02848 | nested_outer_oof |
| polish_4year | full | logistic | 8 | 0.43676 | 0.38613 | 0.49019 | 0.052598 | 0.0367 | nested_outer_oof |
| polish_4year | harmonized | none | 8 | 0.15456 | 0.13298 | 0.18502 | 0.052598 | 0.047018 | nested_outer_oof |
| polish_4year | harmonized | none | 8 | 0.24037 | 0.19477 | 0.29682 | 0.032264 | 0.027761 | transfer_development |
| polish_3year | full | none | 12 | 0.5546 | 0.50508 | 0.59993 | 0.047132 | 0.028798 | nested_outer_oof |
| polish_3year | full | class_weight | 12 | 0.54581 | 0.4963 | 0.58931 | 0.047132 | 0.029167 | nested_outer_oof |
| polish_3year | full | logistic | 12 | 0.3008 | 0.25468 | 0.35093 | 0.047132 | 0.037291 | nested_outer_oof |
| polish_5year | full | none | 4 | 0.77607 | 0.7353 | 0.81765 | 0.069374 | 0.027847 | nested_outer_oof |
| polish_5year | full | class_weight | 4 | 0.75942 | 0.71588 | 0.80229 | 0.069374 | 0.029343 | nested_outer_oof |
| polish_5year | full | logistic | 4 | 0.65415 | 0.6037 | 0.70293 | 0.069374 | 0.037294 | nested_outer_oof |
| polish_5year | harmonized | none | 4 | 0.31499 | 0.27051 | 0.37443 | 0.069374 | 0.054319 | nested_outer_oof |
| polish_5year | harmonized | none | 4 | 0.26548 | 0.21267 | 0.33071 | 0.032264 | 0.028235 | transfer_development |
| taiwan | full | none | unavailable | 0.41225 | 0.34736 | 0.48947 | 0.032264 | 0.023231 | nested_outer_oof |
| taiwan | full | class_weight | unavailable | 0.42287 | 0.3472 | 0.50352 | 0.032264 | 0.022946 | nested_outer_oof |
| taiwan | full | logistic | unavailable | 0.35979 | 0.29412 | 0.43875 | 0.032264 | 0.024262 | nested_outer_oof |

Source: [benchmark_development_metrics](../../outputs/benchmark_development_metrics.csv).

## Final benchmark

| n | positives | base_rate | pr_auc | pr_auc_ci_low | pr_auc_ci_high | pr_auc_definition | trapezoid_pr_auc | roc_auc | brier | ece | capacity | recall_at_cap | precision_at_cap | tau_star | cost_at_tau_star_uncapped | cost_at_cap | descriptive_tau_grid_min | descriptive_grid_min_cost_uncapped | bootstrap_valid_resamples | is_synthetic | dataset | representation | variant | horizon_quarters | evaluation_dataset | evaluation_split | is_transfer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1959 | 103 | 0.052578 | 0.63639 | 0.55442 | 0.71784 | average_precision | 0.67022 | 0.91664 | 0.02751 | 0.008373 | 97 | 0.5534 | 0.58763 | 0.047619 | 664 | 960 | 0.019899 | 657 | 1000 | 0 | polish_4year | full | none | 8 | polish_4year | untouched_holdout | 0 |
| 1959 | 103 | 0.052578 | 0.65794 | 0.57865 | 0.73668 | average_precision | 0.67379 | 0.91866 | 0.026832 | 0.0066991 | 97 | 0.60194 | 0.63918 | 0.047619 | 716 | 855 | 0.039697 | 705 | 1000 | 0 | polish_4year | full | class_weight | 8 | polish_4year | untouched_holdout | 0 |
| 1959 | 103 | 0.052578 | 0.45231 | 0.35799 | 0.55254 | average_precision | 0.49754 | 0.86758 | 0.035621 | 0.0073272 | 97 | 0.49515 | 0.52577 | 0.047619 | 765 | 1086 | 0.034747 | 728 | 1000 | 0 | polish_4year | full | logistic | 8 | polish_4year | untouched_holdout | 0 |
| 1959 | 103 | 0.052578 | 0.1542 | 0.11017 | 0.21549 | average_precision | 0.17811 | 0.74556 | 0.047099 | 0.0021345 | 97 | 0.23301 | 0.24742 | 0.047619 | 1238 | 1653 | 0.049596 | 1184 | 1000 | 0 | polish_4year | harmonized | none | 8 | polish_4year | untouched_holdout | 0 |
| 1364 | 44 | 0.032258 | 0.25393 | 0.16459 | 0.38763 | average_precision | 0.29841 | 0.91346 | 0.027548 | 0.025641 | 68 | 0.45455 | 0.29412 | 0.047619 | 445 | 528 | 0.049596 | 372 | 1000 | 0 | polish_4year | harmonized | none | 8 | taiwan | untouched_holdout | 1 |
| 2101 | 99 | 0.04712 | 0.55181 | 0.45696 | 0.64695 | average_precision | 0.58415 | 0.90948 | 0.028758 | 0.0064629 | 105 | 0.54545 | 0.51429 | 0.047619 | 709 | 951 | 0.084242 | 671 | 1000 | 0 | polish_3year | full | none | 12 | polish_3year | untouched_holdout | 0 |
| 2101 | 99 | 0.04712 | 0.49163 | 0.39989 | 0.58439 | average_precision | 0.52228 | 0.8963 | 0.030742 | 0.0054997 | 105 | 0.48485 | 0.45714 | 0.047619 | 730 | 1077 | 0.044646 | 730 | 1000 | 0 | polish_3year | full | class_weight | 12 | polish_3year | untouched_holdout | 0 |
| 2101 | 99 | 0.04712 | 0.25842 | 0.18713 | 0.34341 | average_precision | 0.26251 | 0.82074 | 0.038921 | 0.0051451 | 105 | 0.39394 | 0.37143 | 0.047619 | 1057 | 1266 | 0.054545 | 982 | 1000 | 0 | polish_3year | full | logistic | 12 | polish_3year | untouched_holdout | 0 |
| 1182 | 82 | 0.069374 | 0.75342 | 0.65964 | 0.83217 | average_precision | 0.77475 | 0.9457 | 0.028096 | 0.0088074 | 59 | 0.62195 | 0.86441 | 0.047619 | 394 | 628 | 0.039697 | 369 | 1000 | 0 | polish_5year | full | none | 4 | polish_5year | untouched_holdout | 0 |
| 1182 | 82 | 0.069374 | 0.75364 | 0.6648 | 0.83415 | average_precision | 0.76959 | 0.94457 | 0.029233 | 0.0096057 | 59 | 0.62195 | 0.86441 | 0.047619 | 369 | 628 | 0.034747 | 369 | 1000 | 0 | polish_5year | full | class_weight | 4 | polish_5year | untouched_holdout | 0 |
| 1182 | 82 | 0.069374 | 0.63443 | 0.52279 | 0.72967 | average_precision | 0.66108 | 0.88427 | 0.037367 | 0.012482 | 59 | 0.53659 | 0.74576 | 0.047619 | 498 | 775 | 0.079293 | 475 | 1000 | 0 | polish_5year | full | logistic | 4 | polish_5year | untouched_holdout | 0 |
| 1182 | 82 | 0.069374 | 0.30784 | 0.22249 | 0.40062 | average_precision | 0.33156 | 0.81971 | 0.05518 | 0.0093427 | 59 | 0.2561 | 0.35593 | 0.047619 | 670 | 1258 | 0.049596 | 670 | 1000 | 0 | polish_5year | harmonized | none | 4 | polish_5year | untouched_holdout | 0 |
| 1364 | 44 | 0.032258 | 0.31366 | 0.20315 | 0.45288 | average_precision | 0.34569 | 0.90958 | 0.02725 | 0.036381 | 68 | 0.56818 | 0.36765 | 0.047619 | 469 | 423 | 0.14364 | 344 | 1000 | 0 | polish_5year | harmonized | none | 4 | taiwan | untouched_holdout | 1 |
| 1364 | 44 | 0.032258 | 0.48644 | 0.34564 | 0.64408 | average_precision | 0.49694 | 0.94545 | 0.021196 | 0.011662 | 68 | 0.68182 | 0.44118 | 0.047619 | 255 | 318 | 0.064444 | 253 | 1000 | 0 | taiwan | full | none | unavailable | taiwan | untouched_holdout | 0 |
| 1364 | 44 | 0.032258 | 0.52532 | 0.38216 | 0.66558 | average_precision | 0.55995 | 0.95405 | 0.020267 | 0.010848 | 68 | 0.72727 | 0.47059 | 0.047619 | 275 | 276 | 0.16838 | 239 | 1000 | 0 | taiwan | full | class_weight | unavailable | taiwan | untouched_holdout | 0 |
| 1364 | 44 | 0.032258 | 0.41127 | 0.2796 | 0.55441 | average_precision | 0.45426 | 0.93229 | 0.023502 | 0.0085743 | 68 | 0.5 | 0.32353 | 0.047619 | 278 | 486 | 0.054545 | 258 | 1000 | 0 | taiwan | full | logistic | unavailable | taiwan | untouched_holdout | 0 |

Source: [benchmark_final_metrics](../../outputs/benchmark_metrics.csv).

## Indian panel evaluation

Not run or not available. No numerical result is inferred.

Scored production replay requires an accepted panel, independently sourced horizon priors and a matching pre-registration lock committed alone before replay. Unscored cases cannot be silently removed to flatter recall.

## Policy and cost

| parameter | value | is_synthetic |
| --- | --- | --- |
| cost_fn | 20 | 0 |
| cost_fp | 1 | 0 |
| alert_frac | 0.05 | 0 |
| tier1_pd | 0.15 | 0 |
| tau_star | 0.047619 | 0 |
| expected_miss_cost_at_tau | 0.95238 | 0 |
| expected_review_cost_at_tau | 0.95238 | 0 |

Source: [app_policy](../../outputs/policy_parameters.csv).

The operational review list uses the registered hard cap and deterministic tie handling. Additional-slot curves are counterfactual cost statistics and do not enlarge the operational list.

For probability p, the expected cost of a miss is p times cost_fn; the expected cost of review is (1-p) times cost_fp. Equating them gives tau_star = cost_fp / (cost_fn + cost_fp). The policy table includes both equal expected costs at that threshold. Capacity is floor(alert_frac times the eligible population); a binding capacity limit further restricts the ranked list. These are policy calculations, not observed borrower losses.

Not run or not available. No numerical result is inferred.

Not run or not available. No numerical result is inferred.

Not run or not available. No numerical result is inferred.

## Attribution and evidence

Native raw-margin TreeSHAP is rescaled to reconcile the nonlinear calibrated log-odds exactly. This path-proportional allocation is not presented as Shapley values of calibrated probability. CHS and overlay terms are linear. Single-driver probability removal effects overlap and are not additive or causal.

Source deltas distinguish borrower documents from roll-forward and peer/universe-context effects, and must telescope between scored endpoints. A missing endpoint produces no invented evidence chain.

## Ablation and detection

Not run or not available. No numerical result is inferred.

Not run or not available. No numerical result is inferred.

Not run or not available. No numerical result is inferred.

Not run or not available. No numerical result is inferred.

Rating lead compares the first pre-event watch-list flag with the earliest sourced sub-investment-grade publication. The median uses paired observed endpoints; missing cases remain listed. Incomplete rating histories do not establish the first-ever downgrade. Calendar-quarter and day differences are both exported.

## Placebo and anti-gaming

Not run or not available. No numerical result is inferred.

Not run or not available. No numerical result is inferred.

Counterfactual intervention inputs never replace source financials or enter the app as financial observations. A scenario that changes no active primary input is labelled ineffective and cannot establish robustness.

## Monitoring and counterfactual policy experiments

Not run or not available. No numerical result is inferred.

Not run or not available. No numerical result is inferred.

Not run or not available. No numerical result is inferred.

## Retrospective archetypes

Not run or not available. No numerical result is inferred.

## Coverage parity

| feature | case_missing | case_present | peer_missing | peer_present | fisher_p | collection_cause | arena_u_eligible | reason | needs_verification | is_synthetic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| total_assets | 10 | 2 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| total_liabilities | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| current_assets | 11 | 1 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| current_liabilities | 11 | 1 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| inventory | 10 | 2 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| receivables | 10 | 2 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| cash_and_st_investments | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| ppe_net | 10 | 2 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| cwip | 10 | 2 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| total_debt | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| st_borrowings | 11 | 1 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| commercial_paper | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| lt_debt | 11 | 1 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| equity | 11 | 1 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| retained_earnings | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| revenue | 10 | 2 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| cogs | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| gross_profit | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| sga | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| depreciation | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| ebit | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| interest_expense | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| pbt | 10 | 2 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| pat | 10 | 2 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| cfo | 10 | 2 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| shares_outstanding | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| related_party_loans_advances | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| related_party_revenue | 12 | 0 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| cash_and_cash_equivalents | 10 | 2 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |
| finance_costs | 10 | 2 | 0 | 0 | unavailable | unknown | 0 | insufficient_cohorts | 1 | 0 |

Source: [coverage_parity](../../outputs/coverage_parity.csv).

## Case catalog

| entity_id | name | sector | event_date | public_date | needs_verification |
| --- | --- | --- | --- | --- | --- |
| INE975G01012 | IL&FS Transportation Networks Ltd | infrastructure_development | 2018-09-28 | 2018-09-28 | 0 |
| INE202B01012 | Dewan Housing Finance Corporation Ltd | housing_finance | 2019-06-04 | 2019-06-05 | 0 |
| INE802G01018 | Jet Airways (India) Ltd | airlines | 2018-12-31 | 2019-01-02 | 0 |
| INE013A01015 | Reliance Capital Ltd | nonbank_finance | 2019-09-09 | 2019-09-20 | 0 |
| INE217K01011 | Reliance Home Finance Ltd | housing_finance | 2019-09-09 | 2019-09-12 | 0 |
| INE752P01024 | Future Retail Ltd | retail | 2020-10-28 | 2020-10-28 | 0 |
| INE335K01011 | Coffee Day Enterprises Ltd (CDEL) | diversified_nonfinancial | 2019-09-10 | 2019-09-10 | 0 |
| INE330H01018 | Reliance Communications Ltd (RCom) | telecommunications | 2017-05-30 | 2017-05-30 | 0 |
| INE872A01014 | Srei Infrastructure Finance Ltd | nonbank_finance | 2021-03-06 | 2021-03-06 | 0 |
| INE703A01011 | Videocon Industries Ltd | consumer_electronics | 2018-06-06 | 2018-06-09 | 0 |
| INE099J01015 | Jaypee Infratech Ltd | infrastructure_development | 2015-09-25 | 2015-09-25 | 0 |
| INE270A01011 | Alok Industries Ltd | textiles | 2017-07-18 | 2017-07-19 | 0 |

Source: [case_catalog](../../outputs/case_catalog.csv).

Case cards are exported for every reviewed case. Before registered evaluation, their status is not assessed rather than an invented hit or miss.

## Limitations

The data acceptance and source-coverage tables above are authoritative. Public data collection, complete peer survival evidence, historical classifications, share counts and regulatory-capital inputs may remain incomplete. Raw bhavcopy returns are unadjusted for corporate actions; cached price indices are not claimed to be total-return indices. Market-only background membership is not claimed to be a debt-ranked complete universe.

The US CHS coefficients are not an Indian probability calibration. Annual-income proxies, universe-relative size and the plan's book-equity variant are explicit adaptations. Unknown priors do not fall back to panel prevalence. Financial-firm ranks are not called calibrated probabilities without a declared probability link.

## Internal EWS workflow appendix

| tier | action | internal_sla_business_days | reference_version | reference_clause | reference_url | interpretation | is_synthetic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tier1 | Escalate this EWS note for human fraud-risk review. Preserve the dated evidence, obtain borrower explanations and record the reviewer's decision under the bank's approved process. | 2 | RBI fraud-risk directions 2024, historical design reference | 3.1.1 | https://systemhealth.rbi.org.in/Scripts/BS_ViewMasDirections.aspx_id%3D12702%281%29.html | internal_workflow_mapping_not_automatic_fraud_classification | 0 |
| tier2 | Request and reconcile supporting records, track unresolved discrepancies and escalate material concerns through the bank's approved EWS process. | 5 | RBI fraud-risk directions 2024, historical design reference | 3.1.1 | https://systemhealth.rbi.org.in/Scripts/BS_ViewMasDirections.aspx_id%3D12702%281%29.html | internal_workflow_mapping_not_automatic_fraud_classification | 0 |
| tier3 | Monitor the cited signals and record follow-up evidence under the bank's approved EWS process. | 10 | RBI fraud-risk directions 2024, historical design reference | 3.1.1 | https://systemhealth.rbi.org.in/Scripts/BS_ViewMasDirections.aspx_id%3D12702%281%29.html | internal_workflow_mapping_not_automatic_fraud_classification | 0 |

Source: [workflow](../../outputs/workflow.csv).

This is a design mapping to the cited historical framework. PRAHARI tiers and review targets are internal settings, not RBI-prescribed classifications or deadlines. A human institution makes any red-flag or fraud determination under its applicable approved process.

## Amendments

{"changed_files": ["configs/delivery.yaml"], "evaluation_rerun": false, "is_synthetic": 0, "models_training_policy_unchanged": true, "new_lock_sha256": "0679ac3a72860f1b6d734f3dbe7305145bc34b3817ad867f185cf1d21f5d50a6", "previous_lock_sha256": "e41cdb6577f6640afb1c388061c73ce020367b640f4e01768f980ccbf70f3dbc", "reason": "User-requested submission documentation segregation: archive file list only; no changes to models, learning code, data, calibration or policy, and no evaluation rerun.", "scope": "benchmark_packaging_only", "time": "2026-10-29T16:00:06.441013+00:00"}


## Reproducibility

Run `run_tests.ps1`, then `run_all.ps1 -Offline -Readiness` for a cached readiness build. Strict production execution preserves all data, registration and final-evaluation gates. Start the offline interface with `run_app.ps1`. The app reads only the exported output bundle.
