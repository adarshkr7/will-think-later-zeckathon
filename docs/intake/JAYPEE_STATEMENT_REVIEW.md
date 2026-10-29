# Jaypee Infratech original statement review

Reviewed on 2026-10-29. Raw originals and immutable receipts are in `data/raw/bse_reports/jaypee_original_2011.pdf` through `jaypee_original_2015.pdf`. Only FY2011?FY2014 are mapped in `configs/sources.yaml`. Original URLs use BSE code 533207 and the exact report-year filename; malformed discovery links are not substituted silently. The FY2015 source remains cached but unreviewed and is not used to assert pre-event availability.

| Source FY | PDF balance sheet | PDF income statement | PDF operating cash flow | Reserve note |
|---|---|---|---|---|
| 2011 | 21 | 22 | not mapped | not mapped |
| 2012 | 20 | 21 | 33 | 23 |
| 2013 | 23 | 24 | 38 | 27 |
| 2014 | 26 | 27 | 42 | 30?31 |

These statements print individual rupees. Rendered balance-sheet and reserve-note pages confirm the rupee glyph; pypdf decodes that source font as a backtick. The literal denomination check is explicitly pinned with the report SHA-256. Amounts are not interpreted as lakh or crore from their apparent size.

FY2011 uses the older net-current-assets presentation. Its total funds employed is not total assets. Gross assets are the printed total funds employed plus the separately printed current liabilities and provisions. Equity is the sum of printed capital and reserves. Current-asset and current-liability totals are the explicit amount-only subtotal lines. FY2012?FY2014 use gross presentation; total liabilities sum the printed non-current and current liability subtotals. Equity uses the printed shareholders-funds subtotal. No dash is filled with zero.

Retained earnings for FY2012?FY2014 mean cumulative earned reserves: total reserves and surplus less the separately printed securities premium reserve. The reviewed complete notes identify general reserve, debenture redemption reserve, surplus and (in FY2014) transfers of retained profits into special reserve / special-reserve-utilization accounts. Those profit allocations are retained; paid-in share premium is excluded. Using the surplus line alone would create a false collapse on the FY2014 reclassification. Both source pages are retained for each calculation, with the balance-sheet page as the primary page. This mapping is specific to these fully reviewed notes, not a rule for arbitrary reserves captions.

Revenue is operations/sales, not total income. Finance costs remain separate from interest-only expense. FY2011 separately printed interest is mapped; aggregate finance costs in later years are not substituted. Operating cash flow follows the original statement's classification, which includes dividend payments. Later reclassified comparatives retain the later report's publication proxy.

No dissemination timestamp has been established for these four annual reports. FY-end plus the configured annual-report lag is used with `date_is_imputed=1`, applied to each source report, including its comparatives. The signing date is not a publication date. The FY2011 business description provides infrastructure/expressway and real-estate classification before the matching cutoff, corroborated by original exchange identity evidence. Human event labels are unchanged.
