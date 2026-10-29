# Housing-finance candidate review

Reviewed on 2026-10-29. Repco Home Finance, Can Fin Homes and GIC Housing Finance are research candidates, not approved peers. Original BSE-hosted annual reports, exact hashes, statement pages, denominations and classification assertions are pinned in `configs/sources.yaml`.

| Candidate | Original reports reviewed | Balance sheet / profit-and-loss PDF pages | Printed units |
|---|---|---|---|
| Repco | FY2015, FY2017, FY2018 | 59/60; 69/70; 65/66 | Individual INR |
| Can Fin | FY2015, FY2017, FY2018 | 102/103; 125/126; 123/124 | INR lakh |
| GIC | FY2015, FY2017, FY2018 | 54/55; 62/63; 71/72 | INR lakh |

Each balance sheet supplies its reported total assets and shareholder equity. Liabilities are the difference between those complete printed amounts. Can Fin's unallotted share-application money stays outside the reported shareholder-equity subtotal. No missing component is set to zero. Original and restated comparative values remain separate publication vintages.

Repco's main-business disclosure, Can Fin's NHB registration disclosure and GIC's NHB/HFC accounting-policy disclosure establish housing-finance classification in the original FY2015 sources. Their publication dates use the annual-report lag, not the audit-signing date.

Can Fin's FY2018 profit has whitespace after a thousands comma. The parser now joins the printed grouping before identifying columns; it does not treat the leading group as a note number. GIC's FY2018 PDF uses an encoded font. Both original statement pages were rendered and visually inspected. Only the legible current numeric column is imported; the encoded comparative column is excluded. Embedded font-control glyphs must not be treated as physical line breaks.

Can Fin's original reports show the same legal-company CIN and disclose a 2017 share subdivision. The historical-to-successor security link still needs dated original evidence. Do not merge different ISINs by ticker or infer the successor ISIN from memory.

The cached financial XBRL samples contain profit-and-loss data but do not provide the missing balance sheets. One Repco sample's declared unit and reported scale disagree with its original annual statement, so it is not imported. An XML attachment reused in a later filing keeps the later publication date.

Full-window survival review, applicable stressed-survivor evidence, matching-date coverage, security continuity and frozen peer selection remain outstanding. An empty IBBI search does not establish nondefault. The new public IBBI announcement collector stores unreviewed discovery metadata separately and does not assign labels. Only the corporate-debtor column is searched; applicant and insolvency-professional names cannot establish debtor matches. Announcement dates are not substituted for CIRP commencement dates.
