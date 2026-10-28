# Videocon statement review

Reviewed against extracted text and rendered original PDF pages on 2026-10-28. Imported observations are in `data/manual/financial_evidence.csv`; current collection counts are generated in `outputs/collection_status.csv`.

| Original source | SHA-256 | PDF pages reviewed for imported values |
|---|---|---|
| [Annual report 2014](https://www.videoconindustriesltd.com/Documents/10078.pdf) | `34f059556fd9f03b94b04177c3c49f21e6216a2812d6c280fdd5d6c5c2c43570` | 44 |
| [Annual report 2015](https://www.videoconindustriesltd.com/Documents/Videocon%20Industries%20Ltd_2015.pdf) | `6b9fc40f13d6955a0a356baed5e1cbb8a6b051e8323dcbe4d4073fc5b7658c44` | 58, 59, 60, 64 |

Both sources are already cached with receipts under `data/raw/videocon/`. Amounts are explicitly INR million; the manual evidence retains that denomination. Each field retains its original source URL and PDF page position.

The earlier report's income and cash flows cover eighteen months ending December 2014. None were entered as annual flows. Its December 2014 and June 2013 balance-sheet observations are retained with their actual dates. The later report provides a twelve-month December 2015 income/cash-flow column and comparative balance-sheet stocks; comparative flows are excluded. Later comparative stocks keep the later source report's dissemination lag.

Imported fields are the printed total assets, current-assets and current-liabilities subtotals, shareholders' funds subtotal, inventory, trade receivables, tangible fixed assets, CWIP, long-term and short-term borrowings, net operating revenue, PBT, PAT, finance costs, CFO, cash and cash equivalents, and the printed current portion of long-term borrowings. Cash-and-bank balances are not substituted for cash equivalents. Net operating revenue excludes the separately shown excise duty.

No total-liabilities or retained-earnings value was improvised. Reserves and surplus contain multiple distinct reserves; their total is not copied into retained earnings. Finance costs do not stand in for interest expense. Actual dissemination dates are unresolved, so the configured annual-report lag is applied to the report's own period end with `date_is_imputed=1`; auditor signing dates are not treated as publication dates.

The imported fields improve source coverage but do not establish a complete financial history or pass panel acceptance. The team still needs the missing core fields and original reports covering the required pre-event history.
