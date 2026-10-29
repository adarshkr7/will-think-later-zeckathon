# Alok and Videocon: annual-length history review

Reviewed on 2026-10-29. The core-history check now accepts both companies. This closes the missing annual-length financial observations, not the separate governance, peer, market-adjustment or calibration requirements.

Original statement mappings, units, pages and hashes are in `configs/sources.yaml`. The signed interval definitions and source hashes are in `configs/financial_reconciliations.yaml`; reviewed operand cells are in `data/manual/financial_intervals.csv`. Rebuild with `python -m scripts.02l_reconcile_annual_flows`. Its numerical/source audit is `outputs/financial_reconciliations.csv`.

| Company / target end | Exact flow reconciliation | Original source pages |
|---|---|---|
| Alok, September 2013 | April 2012–September 2013 less April–June 2012 and July–September 2012 | Original FY2013 annual report, PDF 153; June/September 2013 results, PDF 1, explicitly labelled comparative quarters |
| Alok, March 2015 | October 2013–March 2015 less October 2013–March 2014 | Original FY2015 annual report, PDF 119; March 2014 half-year results, PDF 1 |
| Videocon, December 2014 | July 2013–December 2014 less July–September 2013 and October–December 2013 | Original FY2014 annual report, PDF 45; original NSE result pages, sequences 112665 and 115369 |
| Videocon, March 2017 | January 2016–March 2017 less January–March 2016 | Original FY2017 annual report, PDF 55; original NSE result page, sequence 1007194 |

Each resulting interval is exactly twelve months. The implementation checks every boundary segment for weight one inside the target year and zero outside it; a gap, overlap or wrong end date fails. It converts only explicitly printed units. These are reconstructed TTM income flows, not audited twelve-month statements. No proportional annualisation or extrapolation is used. The original extended-period totals are kept as interval operands rather than silently relabelled as annual financial inputs.

The Alok result PDFs are image scans. Their comparative headers and the required cells were rendered and visually reviewed; unreadable cells were not guessed. The repeated values in the original annual statements corroborate the extended totals. Original and later restated balance-sheet observations remain separate vintages.

The latest operand publication date controls each reconstructed flow. Original NSE filing metadata supports known dissemination timestamps. Unknown quarterly dissemination uses the results lag from the source document's reporting end, including when it reports an older comparative. Videocon FY2014 uses the later original NSE annual-archive date proxy plus one day; FY2017 uses its recorded March 2018 dissemination, not an earlier default lag. Publication evidence is cached with receipts in `data/raw/nse_annual_index/` and `data/raw/nse_financial_index/`.

Alok's original and comparative balance sheets and reserve notes provide the stock fields for the September 2013, March 2015 and March 2016 observations. Earned reserves include capital/debenture redemption reserves, general reserve and the retained surplus/deficit; paid-in premium, capital reserve, employee-option and currency/hedging balances are excluded. Videocon uses the same earned-reserve definition from the individually reviewed closing reserve rows. Its ozone grant is deferred income outside shareholder equity and remains within liabilities derived from assets less equity.

The later Alok Ind AS comparative substantially changes assets and equity. Its complete printed asset/liability/equity triplet is now mapped together at the later publication date; retaining only restated assets would produce a false mixed-vintage accounting failure. This later report is unavailable before Alok's event and does not contribute to its pre-event history count.

Alok's fiscal-end change leaves a gap between selected annual-length windows. Existing feature construction requires exact calendar-year lags: a missing same-date prior year stays missing. A coverage pass does not turn the nearest older observation into a one-year growth denominator. No event definition, peer rule, model weight or acceptance threshold changed.
