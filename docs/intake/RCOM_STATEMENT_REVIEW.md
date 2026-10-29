# Reliance Communications original statement review

Reviewed on 2026-10-29. Receipt-protected original BSE reports for FY2013?FY2016 are mapped in `configs/sources.yaml`; raw files are `data/raw/bse_reports/INE330H01018_annual_*.pdf`.

| Source FY | PDF balance sheet | PDF income statement | PDF reserve note |
|---|---|---|---|
| 2013 | 53 | not mapped | not mapped |
| 2014 | 55 | 56 | 62 |
| 2015 | 69 | 70 | 76 |
| 2016 | 71 | 72 | 78 |

The printed denomination is INR crore. Rendered original balance sheets and reserve notes were inspected. The old-format statements interleave each year's line item and subtotal: reviewed positions select the printed total shareholders' funds, current assets, current liabilities and non-current liabilities. Total liabilities explicitly sum the two printed liability subtotals. Total assets are the sheet's gross total, not a debt measure.

Retained earnings are the separately identified closing surplus/deficit in the profit-and-loss account, not total reserves and surplus. Capital, premium, restructuring, currency and revaluation reserves are excluded from that caption. Finance costs remain distinct from interest-only expense. The gross depreciation/amortisation caption is retained without concealing the separately printed reserve withdrawals, exceptional adjustments or tax credits. PAT is the actual printed after-tax profit/loss; a tax benefit is not corrected to make it resemble pre-tax earnings.

The FY2015 report restates parts of FY2014; FY2016 also reclassifies comparative line items. Original and subsequent vintages retain different source-publication proxies. Source FY-end plus the configured annual-report lag is used with `date_is_imputed=1`; signing dates are not dissemination dates. The FY2013 company profile supplies contemporaneous telecommunications classification and assets before the matching cutoff. The human earliest-event labels and original 2018-05-15 CIRP commencement date are unchanged.
