# Reliance Home Finance FY2017 partial statement review

The original publisher FY2016?FY2017 report was recovered through the [official financials page](https://www.reliancehomefinance.com/financials/) and cached with an immutable receipt at `data/raw/rhfl/rhfl_annual_2017.pdf`. The mapping in `configs/sources.yaml` pins its SHA-256. PDF page 26 is the standalone balance sheet and page 27 the income statement, both in INR crore. The balance sheet was rendered and inspected.

Reported total assets, long-/short-term borrowings, tangible assets, operations revenue, PAT, PBT, finance costs and depreciation are mapped. Current-year equity sums the three printed shareholder components, including share capital suspense. The comparative suspense cell is a dash: the comparative equity sum and liabilities derived from it remain blank with `needs_verification=1`. Missing operands are not skipped. The liabilities calculation is algebraic (assets less complete equity), not independent liability verification.

The FY2018 report's financial highlights use net worth and equity-share-capital captions that do not equal complete book shareholders' funds. They are not substituted for equity. Its FY2017 comparative balance sheet also differs from the original FY2017 report; these are separate later-vintage sources, not overwrite candidates. The source period and conservative publication lag are retained, and the audit signing date does not become a dissemination date.

This is a partial import and does not pass the company's three-year core history gate. The legacy FY2015/FY2016 publisher links could not be recovered on the current host (cached 404 responses); they remain a public-source recovery task, with no invented historical values.
