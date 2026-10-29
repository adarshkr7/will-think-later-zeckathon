# Future Retail original statement review

Reviewed on 2026-10-29. Original receipt-protected BSE reports are cached as `data/raw/bse_reports/INE752P01024_annual_2017.pdf` and `INE752P01024_annual_2019.pdf`. Exact source URLs, hashes, labels and column counts are in `configs/sources.yaml`.

| Source FY | PDF balance sheet | PDF income statement | PDF equity changes/note |
|---|---|---|---|
| 2017 | 89 | 90 | 91 |
| 2019 | 146 | 147 | 164 |

Denomination is INR crore. FY2017 has three balance-sheet columns; only the two explicitly headed March year ends are mapped, with the April opening transition balance excluded. FY2017 flow extraction is restricted to the current year: earlier restructuring/period comparability has not been established. FY2019 contains current-year and FY2018 comparative statements; those comparatives retain FY2019 availability.

Total liabilities sum the separately printed non-current and current liability totals. Equity is the explicitly printed total. Retained earnings use the reviewed closing balance within the named retained-earnings section, with exact repeated-label count and occurrence; capital reserves, premium, suspense, options and convertible-debenture equity components are excluded. Negative retained balances remain negative.

Cost of goods sold is the explicit signed sum of purchases of stock-in-trade and changes in stock-in-trade inventory. The two note references on depreciation are excluded with reviewed amount positions. Revenue is operations revenue; PAT excludes other comprehensive income. Finance costs are not treated as interest-only expense. Unknown dash cells remain unknown and flagged.

Publication is source FY-end plus the configured annual-report lag, with `date_is_imputed=1`. Signing dates are not publication dates. FY2017's directors' report describes the retail business and store operations before the matching cutoff, corroborated by original quote identity evidence. Company restructuring remains a comparability limitation; it does not justify merging other Future-company ISINs or using later constituent data earlier.
