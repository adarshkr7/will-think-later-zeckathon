# Supplied public-source review

Generated from `outputs/supplied_source_review.csv`; original files and integrity receipts remain in the ignored raw cache.

The Indian data must meet the implementation plan's identity, accounting-basis and publication-date requirements before it can enter the panel. Candidate sources do not waive those checks. Benchmark numeric rows are excluded from this review.

## Financial Distress (Kaggle)

[discovery_only](https://www.kaggle.com/datasets/shebrahimi/financial-distress/data). Anonymous company/time identifiers and x-fields cannot establish the Indian panel or dated original filings; outside the declared foreign benchmark.

Cache: `data/raw/kaggle/shebrahimi_financial-distress_v1.zip`. SHA-256: `9c06f99fc4e74e0aac2fb5f871931f19c3e3890e6bc8bffeffb66162924d69ab`.

Observed audit fields: rows_inspected: 3672; files: 1; columns: 86.

## NSE shares 2021–2025 (Kaggle)

[discovery_only](https://www.kaggle.com/datasets/amritanshukush/nse-shares-data-2021-2025). Selected current stocks and a later date window do not replace survivorship-aware bhavcopies; no dated ISIN mapping or documented adjustment basis in the supplied schema.

Cache: `data/raw/kaggle/amritanshukush_nse-shares-data-2021-2025_v1.zip`. SHA-256: `7980db695e0e3c03415cb4265575e2d524d19210eeef6223a0e94689d62efa2a`.

Observed audit fields: rows_inspected: 9856; files: 8; columns: 7.

## Indian company financial dataset (Kaggle)

[discovery_only](https://www.kaggle.com/datasets/sayujsreenivasan/indian-company-financial-dataset). No filing timestamps, original period-end dates, ISIN, denomination or accounting basis. Total Liabilities is the funding-side total including equity, so it cannot map to PRAHARI total_liabilities. Verify candidate names against original statements.

Cache: `data/raw/kaggle/sayujsreenivasan_indian-company-financial-dataset_v1.zip`. SHA-256: `968e694c789f59cdc198a2809a4cc0d1ba09cff4979811b1023bcc7b10c6b412`.

Observed audit fields: rows_inspected: 8991; files: 1; columns: 65; companies: 999; earliest_year: 2006; latest_year: 2026; funding_total_equals_assets_rows: 8991; funding_components_reconcile_rows: 8991.

## Top Indian stocks market insights (Kaggle)

[discovery_only](https://www.kaggle.com/datasets/rameshmaity/top-indian-stocks-market-insights-dataset). A current cross-sectional snapshot does not establish historical quarterly financial vintages, listing eligibility or pre-event availability.

Cache: `data/raw/kaggle/rameshmaity_top-indian-stocks-market-insights-dataset_v1.zip`. SHA-256: `735e4290b1e6df7229419a36b3fc7a2525d6482f635b22351bf0835d95f521cb`.

Observed audit fields: rows_inspected: 2650; files: 1; columns: 12.

## nse2r

[reference_only](https://github.com/rsquaredacademy/nse2r). R retrieval package documentation, not a frozen historical dataset; existing Python collectors cache original exchange files with receipts. Downloaded reference code is not executed.

Cache: `data/raw/github_reference/nse2r_README.md`. SHA-256: `a370e3d1c45f97c7e4b38d8b66491035e6ac28a90e8a3b8d2aca4aa3444bb0c1`.

## Taiwanese bankruptcy prediction (UCI)

[original_benchmark_already_integrated](https://archive.ics.uci.edu/dataset/572/taiwanese+bankruptcy+prediction). Original predeclared foreign benchmark. This source review checks archive integrity only; it does not open numeric rows or reserved membership.

Cache: `data/raw/taiwan/taiwan.zip`. SHA-256: `c346f5ad2618cb198e7ed8306cf2f31fe3bb2ec60acdbbe1736788d50f269aac`.

## Company bankruptcy prediction (Kaggle)

[duplicate_benchmark](https://www.kaggle.com/datasets/fedesoriano/company-bankruptcy-prediction). Uploader describes the same Taiwanese bankruptcy source, not an independent validation population. Numeric rows are not opened by this review.

Cache: `data/raw/kaggle/fedesoriano_company-bankruptcy-prediction_v2.zip`. SHA-256: `47eb02b070a1155d760445434e6b3b4ecc1fe1c9e2c064252485466cbbd490b9`.

## IL&FS Financial Services annual report FY2018

[separate_entity_original](https://www.ilfsifin.com/pdf/IFIN-Annual-Report-2017-18.pdf). Genuine original report for IL&FS Financial Services. This legal entity is separate from the listed ITNL case; its financial values cannot be substituted for ITNL.

Cache: `data/raw/ilfsifin/ifin_annual_2018.pdf`. SHA-256: `86b273557fdceb0825136a82d97826226ef02904ec390cf0b20558e1c29e0cf6`.

Observed audit fields: pages: 162.

## IIFCL annual report FY2017

[separate_entity_original](https://www.iifcl.in/images/FileUploaded/AnnualReport1pdf05122019132624.pdf). Original India Infrastructure Finance Company FY2016–17 report. IIFCL is distinct from IL&FS, IFIN and ITNL; no case substitution or group membership is inferred.

Cache: `data/raw/iifcl/iifcl_user_annual_report.pdf`. SHA-256: `d4450037a2217f92332d5225db16c999a7f8f62fb224c1a2ba7f142197fcc190`.

Observed audit fields: pages: 208.
