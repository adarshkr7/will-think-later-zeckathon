# DHFL original-statement review

Reviewed original exchange-hosted reports in `data/raw/bse_reports/`, with downloader receipts. All mappings and source hashes are pinned in `configs/sources.yaml`.

| Report | Reviewed PDF pages | Scope |
|---|---|---|
| FY2015 | 54, 140 | Historical HFC business classification and original FY2015 standalone balance sheet |
| FY2016 | 145–146 | Standalone balance-sheet columns; current-year income statement only |
| FY2017 | 162–163 | Standalone balance sheet and income statement, with separately dated comparatives |
| FY2018 | 156–157 | Standalone balance sheet and income statement, with separately dated comparatives |

The statement pages and earlier business-classification page were rendered and visually inspected. Amounts are INR lakh. PDF text occasionally splits a thousands comma into separate font runs; the extractor removes whitespace immediately before a numeric comma, without joining separate amount columns.

Total liabilities are an explicitly reviewed sum of the printed **total non-current liabilities** and **total current liabilities** on the same page, basis, denomination and year column. This is a derived aggregate from observed subtotals, not an independently printed figure. Its components are declared in the source mapping and tested against a hand-computed fixture. Any missing component makes the sum unknown. Equity uses the printed shareholders' funds subtotal, including money received against share warrants where the original statement includes it. The accounting-identity audit independently checks the resulting totals.

The FY2016 income statement prints a duplicated current-year heading over its comparative column. That comparative flow column is excluded; no correction is guessed. Its balance sheet clearly identifies the two years and remains usable. Later reports contain reclassified comparative amounts, so their figures are retained as later vintages rather than replacing the original FY2015/FY2016 observations at earlier cutoffs.

FY2018 capital work in progress is printed as a dash and stays unknown. Finance costs remain separately named. Unreviewed cash components, interest-only expense, retained earnings, NBFC metrics and other inputs remain empty. A cached FY2019 report has not been imported.

Publication dates remain unknown and use the configured annual-report lag from each **source** report's period end, including comparative figures. Signing and AGM dates are not substituted for dissemination dates. No event date or inclusion rule changed. Complete core financial-year coverage does not establish complete NBFC inputs, peers, market coverage or production acceptance.
