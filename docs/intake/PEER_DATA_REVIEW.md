# Received peer-data review

Reviewed all 9 received CSVs: 208 claim rows, covering 51 claimed security IDs and 12 case groups. This is an intake review, not approval of a completed peer panel. Original files are unchanged; immutable received copies and receipts are in data/raw/manual/.

Source: `outputs/peer_intake_review.csv`. The audit contains no copied unverified financial values.

| Check | Flagged rows |
|---|---:|
| historical_security_id_differs | 10 |
| financial_period_ends_after_matching_cutoff | 46 |
| claimed_survival_starts_after_required_window | 2 |
| differs_from_reviewed_original | 8 |
| matching_quote_identity_not_verified | 6 |

## Findings requiring correction

The last batch also uses a case identifier that does not match the reviewed event catalog (submitted INE270A01029 versus Alok event INE270A01011). Those case mappings remain unresolved; cutoff checks cannot be certified for their rows without an original continuity/mapping source. The flagged-row counts below do not imply that unresolved rows passed.

- Publication dates in the submissions are collection dates. Matching financials and classifications still need original pre-cutoff disclosures. Retrospective survival verification can be later; it must not enter model inputs.
- Some submitted FY periods end after the matching date. Those observations cannot supply earlier matching assets, even if their figures are otherwise correct.
- Original quote checks show historical ISIN changes and a Repco identity discrepancy. A later split/rename needs a dated continuity chain; it is not automatically evidence that the company is ineligible.
- Provided financial files omit printed units and accounting basis. Conditional comparisons against the reviewed housing-finance statements found both rounded agreements and discrepancies; neither alone approves the rows. Other original-statement comparisons remain pending.
- All generic IBBI-only survival assertions remain unsupported. Positive annual auditor evidence has now been reviewed separately for Can Fin, GIC Housing and Repco. The available IBBI index was also cross-checked; empty matches are only corroboration, not the survival proof.
- MEP Infrastructure has material contrary evidence: CARE reported ongoing debt-servicing delays and a D rating on 2020-08-13, within the claimed ITNL survivor window. The later April 2021 withdrawal is not treated as an automatic upgrade/cure. Its blanket nondefault claim is not accepted.
- Same-sector membership and the stressed-survivor requirement must follow sourced historical business information and the frozen selection rule. Blue Dart must not be assigned to airlines solely to fill a slot.

## Original source references

- [MEP CARE release, August 2020](https://www.careratings.com/upload/CompanyFiles/PR/MEP%20Infrastructure%20Developers%20Limited-08-13-2020.pdf), cached with receipt as data/raw/care_peers/mep_20200813.pdf.
- [MEP CARE withdrawal, April 2021](https://www.careratings.com/upload/CompanyFiles/PR/19042021061742_MEP_Infrastructure_Developers_Limited.pdf), cached with receipt.
- [Blue Dart FY2015 original annual report](https://bluedart.com/documents/20182/380977/annualreport2014-15/4a52cf7b-5013-91fc-2e77-d500703d7449), cached with receipt.
- Housing-finance original statements and page references are linked per row in outputs/peer_intake_review.csv; annual auditor evidence is indexed in outputs/peer_survival_source_review.csv.

No submitted batch is blindly promoted. The canonical source-backed replacements remain separately versioned, and the full panel acceptance gate remains in force.
