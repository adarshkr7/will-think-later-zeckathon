# Srei standalone statement review

Original publisher reports are cached with receipts in `data/raw/srei/`. Source URLs, exact SHA-256 hashes, denominations, year columns and reviewed table rules are pinned in `configs/sources.yaml`.

Rendered and inspected FY2017 PDF pages 81, 151–152 (business classification and printed statements 134–135), FY2018 PDF pages 144–145 (printed 142–143), and FY2019 PDF pages 128–129 (printed 126–127). The statements state amounts in rupees lakh, spelled “Lacs”. Standalone figures are kept separate from the reports' consolidated statements. The original FY2017 report provides matching-period financial and classification evidence without backdating the later report's comparatives.

The earlier balance sheet prints equity and the current/non-current liability subtotals on amount-only lines. The extractor uses reviewed anchors and offsets. Total liabilities are the exact sum of the two printed liability subtotals; no missing components are assumed to be zero.

The FY2019 Ind AS balance sheet uses financial/non-financial categories and does not print a separate liability subtotal. Equity is the sum of the two stated equity components; total liabilities are explicitly derived as total assets minus that complete equity subtotal. This accounting identity is a derived figure, not independent liability evidence, and its identity-audit pass is consequently algebraic. Any missing operand makes the result unknown. The reviewed sheet has no minority-interest component in its standalone equity block.

The FY2019 balance sheet includes an opening transition column. Only the two explicitly mapped March year-end columns are imported; the April opening date is not relabelled as a prior fiscal year. Ind AS restated comparatives retain the FY2019 source-report publication timing and do not replace original FY2018 values at earlier cutoffs.

PAT is the profit after tax line, excluding other comprehensive income. Aggregate finance costs are not labelled interest-only expense. Combined depreciation/amortisation/impairment expense is not substituted for narrower depreciation. Unknown publication dates use the configured annual-report lag from the source report's period end. Audit signing dates do not establish dissemination.

NBFC asset-quality, ALM, regulatory-minimum and other unreviewed fields remain unresolved. Core annual-history coverage does not establish complete financial-track scoring or panel acceptance.
