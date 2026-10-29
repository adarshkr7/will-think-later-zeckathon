# Peer research guide: corrected collection rules

Reviewed on 2026-10-29 against AGENTS.md, PROJECT_IDEA.md and IMPLEMENTATION_PLAN.md. The earlier draft is preserved with a receipt under `data/raw/manual/peer_research_guide_received_ec499faeeb0051a7.md`.

The earlier draft's estimated asset figures, suggested classifications and statements about safety are unverified research leads. Do not copy those estimates into production data. Several instructions in that draft permitted look-ahead or unsupported survival claims; the rules below supersede them.

## Find candidate names, then collect original evidence

Current Screener/market websites can help discover names and original document links. A current page is not proof that today's restated historical figures were available at the matching date. Candidate names already submitted are retained as leads; they are not rejected merely because a source field needs correction.

Use the exact case matching dates in `outputs/team_collection_windows.csv`, checked against the human-reviewed events and configured matching lag. Use the latest original disclosure that was actually public strictly before that date. Never use a later FY as a proxy: an FY2018 statement cannot supply October 2017 matching assets, and an FY2014 statement cannot supply September 2012 matching assets. Unknown publication dates use the configured conservative lag from the source reporting period; do not backdate a current webpage to the historical FY.

## What each financial observation needs

Record the issuer/security identity, actual reporting end, standalone/consolidated basis, printed unit, original document URL, PDF page, publication date and verification flags. Keep incomplete wide rows pending, or provide individual sourced cells for `financial_evidence.csv`. Exact headers are in `configs/manual.yaml`; Codex handles conversion and importing.

Total assets and liabilities can support initial size research, but they do not complete the required peer histories or features. Retain original precision. Do not infer liabilities from a loosely named website row, assume units, mix standalone and consolidated columns, or treat a dash as zero. Extended reporting periods require exact subperiod reconciliation for annual flows.

## Identity and sector

Verify the security that existed at the matching date against original exchange records. A later stock split, merger or rename can change the ISIN or ticker; preserve a dated continuity chain. Do not replace the legal issuer by another company with a similar name.

Source the historical business classification independently. Do not set `sector` equal to the matched case merely to make it eligible. Logistics/courier firms are not automatically airlines. A lack of eligible same-sector firms is a reportable gap, not permission to broaden a sector silently.

## Survival is a full-window evidence check

An empty IBBI search, continued share trading, a current normal rating or the absence of a search-engine result does not establish historical nondefault.

Collect affirmative original evidence across the complete required window, such as annual auditor repayment assertions with their actual scope and CRA histories. Cross-check original insolvency/default notices and identity changes. A notice's announcement date is not automatically CIRP commencement. Apply the documented uncured-D rule consistently; a withdrawal is not automatically an upgrade or cure. A CRA report of payment delays is material contrary evidence and must be resolved.

A later source may support retrospective cohort/survival verification. Its true publication/verification date stays later, and the survival metadata never enters historical model features. This is different from matching assets and sector information, which must already have been public before the matching cutoff.

## Selection and handoff

Provide a broad evidence-backed candidate pool. The configured sector/asset-distance rule and stressed-survivor requirement determine selection; do not label a company safe from reputation or manually choose peers to improve results. Minimum unique-company and per-case requirements stay visible in the acceptance output.

Place original reports/releases or direct original document links with each batch. Existing batch CSVs remain preserved as received; missing flags are not silently treated as verified. Codex checks the sources, records corrections, and publishes only accepted rows into the canonical tables. The current row-level intake review is `outputs/peer_intake_review.csv`.

Authoritative references: `docs/TEAM_DATA_COLLECTION_PLAN.md`, `docs/DATA_REQUESTS.md`, `configs/manual.yaml`, `configs/india.yaml`, and the generated acceptance/coverage outputs.
