# Reliance Home Finance FY2017 partial statement review

The original publisher FY2016?FY2017 report was recovered through the [official financials page](https://www.reliancehomefinance.com/financials/) and cached with an immutable receipt at `data/raw/rhfl/rhfl_annual_2017.pdf`. The mapping in `configs/sources.yaml` pins its SHA-256. PDF page 26 is the standalone balance sheet and page 27 the income statement, both in INR crore. The balance sheet was rendered and inspected.

Reported total assets, long-/short-term borrowings, tangible assets, operations revenue, PAT, PBT, finance costs and depreciation are mapped. Current-year equity sums the three printed shareholder components, including share capital suspense. The comparative suspense cell is a dash: the comparative equity sum and liabilities derived from it remain blank with `needs_verification=1`. Missing operands are not skipped. The liabilities calculation is algebraic (assets less complete equity), not independent liability verification.

The FY2018 report's financial highlights use net worth and equity-share-capital captions that do not equal complete book shareholders' funds. They are not substituted for equity. Its FY2017 comparative balance sheet also differs from the original FY2017 report; these are separate later-vintage sources, not overwrite candidates. The source period and conservative publication lag are retained, and the audit signing date does not become a dissemination date.

This is a partial import and does not pass the company's three-year core history gate. The legacy FY2015/FY2016 publisher links could not be recovered on the current host (cached 404 responses); they remain a public-source recovery task, with no invented historical values.


## Follow-up: core history resolved

The original FY2017 scheme notes on PDF pages 65?66 state that the previously approved FY2016 accounts were not reopened and all scheme entries were booked in FY2017. This establishes the applicability of the suspense-account item: FY2016 shareholders' funds use the printed share capital and reserves, with the scheme note retained in the evidence chain. The earlier unresolved dash-based rows remain preserved; no blanket dash-to-zero rule was introduced.

The FY2018 original balance sheet and income statement are on PDF pages 65?66 of the BSE copy. Its preference-share note on PDF page 74 records the full allotment in August 2017, resolving the current suspense-account applicability. Book shareholders' funds include the printed paid-up preference capital and reserves. Regulatory net worth is not substituted. The actual NSE September 2018 dissemination timestamp is retained. Both statement pages were reviewed, including the spaced thousands groups.

FY2016, FY2017 and FY2018 now pass the three-year core-history check. This does not certify complete historical NBFC scorecard inputs or earlier matching-quarter availability. An attempted original March 2016 half-year PDF is truncated and lacks an EOF marker; its cached bytes/receipt are retained and no fields are imported from it. The separate supplied September 2017 interim intake remains quarantined pending its own review.
