# Reliance Capital standalone statement review

Reviewed and rendered the original exchange-hosted FY2015 report (business profile on PDF page 7; standalone balance sheet on PDF page 59, printed 58), plus the FY2017 and FY2018 reports, PDF pages 67–68 (printed 66–67) in each. The original FY2015 evidence supports the earlier matching cutoff. Cache filenames, URLs, SHA-256 hashes, labels and column positions are pinned in `configs/sources.yaml`.

Amounts are INR crore. These PDFs print space-separated thousands and, in the earlier report, split label fragments under plain text extraction. The mapping explicitly opts into layout extraction. Only single spaces immediately before a three-digit number group are joined; the wider gaps between reviewed amount columns remain intact. This normalization is not applied to unreviewed tables.

Equity, current assets and current liabilities use the printed subtotals interleaved with line-item amounts. Total liabilities are derived from the printed current and non-current liability subtotals on the same standalone sheet. Their calculation remains explicit in the pinned source mapping. No absent liability components are treated as zero.

PAT uses the total after-tax line, including the separately reported discontinued operation in the FY2017 comparative. Finance costs remain separate from interest-only expense. Cash/bank balances and other unreviewed definitions are not silently mapped to narrower fields.

The later report changes comparative balance-sheet amounts. Both original and restated vintages retain their own source-report publication timing. Unknown publication dates use the configured annual lag from the source report end, including comparative columns; signing dates are not dissemination dates. These imports do not certify complete NBFC metrics, peer eligibility or final panel acceptance.
