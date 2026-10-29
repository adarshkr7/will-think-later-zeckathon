# Jet Airways original statement review

Reviewed on 2026-10-29. Original BSE reports, with immutable receipts, are cached as `data/raw/bse_reports/INE802G01018_annual_2015.pdf`, `INE802G01018_annual_2017.pdf` and `INE802G01018_annual_2018.pdf`. Exact URLs, hashes, labels and column counts are in `configs/sources.yaml`.

| Source FY | PDF balance sheet | PDF income statement | PDF retained-earnings note |
|---|---|---|---|
| 2015 | 72 | 73 | not mapped |
| 2017 | 85 | 86 | 93 |
| 2018 | 91 | 92 | 115 |

The denomination is INR lakh. Rendered balance sheets and reserve notes were checked. Old-format liability subtotals are summed explicitly, and shareholders' funds use the printed subtotal, preserving negative equity. FY2018 has explicit total assets, total equity and total liabilities. The opening 1 April 2016 column is excluded from FY mappings. The capital-work-in-progress and cash-equivalent note suffixes are explicitly pinned so note numbers cannot shift amount columns.

The FY2017 reserve note's closing accumulated deficit is mapped separately from total reserves and surplus. FY2018 directly prints retained earnings. Paid-in premium, currency translation, revaluation and other reserves are not silently treated as the accumulated profit/deficit caption. This differs from Jaypee's explicitly reviewed earned-reserve aggregation and is a source-definition limitation, not interchangeable raw reserve captions.

The FY2018 report restates FY2017 on transition to Ind AS. These large changes are retained at the later source's availability, alongside the original FY2017 observations. Opening transition figures do not replace earlier annual records. Accounting-standard discontinuities must not be described automatically as fraud. Income uses operations revenue and profit/loss after tax; other comprehensive income is separate. Finance costs remain separate from interest-only expense. Broad cash-and-bank balances are not mapped to narrow cash equivalents.

Publication uses source FY-end plus the configured annual-report lag with `date_is_imputed=1`; audit signing dates are not dissemination dates. The FY2015 company letter provides an earlier aviation classification, corroborated by original exchange identity evidence. The human event date and global uncured-D rule are unchanged.
