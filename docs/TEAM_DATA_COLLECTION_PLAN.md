# Team manual-data collection plan

Prepared for PRAHARI on 2026-10-28. Work from the repository root. This plan is for evidence collection; Codex will import files, create cache receipts, validate schemas, select peers, rebuild features and run the registered pipeline.

## 1. What needs to be unblocked

Current generated status: **12 reviewed cases; 0 verified matched peers.** The panel still fails peer, stressed-survivor, market and complete-financial-history acceptance. See the linked outputs for the latest counts; cached sources and partial fields are not complete histories.

The event dates already verified by the human are complete for the reviewed search. Do not spend time repeating that work or changing event definitions. The critical gaps are historical financials, eligible peers, publication timing, share counts and symmetric soft-signal coverage. Raw daily market collection is already automated.

Authoritative files:

- [Current requests](DATA_REQUESTS.md), [current acceptance failures](../outputs/panel_acceptance.csv), and [financial-history gaps](../outputs/financial_coverage.csv).
- [Existing source catalog](../outputs/source_catalog.csv): check this before downloading another copy.
- [Exact schemas](../configs/manual.yaml), [selection and coverage settings](../configs/india.yaml), and [sealed input contract](SEALED_INPUT_CONTRACT.md).
- [Company date windows](../outputs/team_collection_windows.csv): machine-readable companion to this plan.

## 2. Assign people to workstreams

Use these role names as placeholders for your team members. One person may cover more than one ordinary workstream. Keep the sealed collector independent of modelling and public-case evaluation.

| Owner | Workstream | First deliverable | Priority |
|---|---|---|---|
| A: financial collector | Original financial statements for cases and candidate peers | One complete case packet, then cases in the table below | P0 |
| B: peer/evidence collector | Historical sector roster, matching-date assets/liabilities and survivor evidence | A sourced candidate pool for the same case as A | P0 |
| C: disclosure collector | Shares, pledge filings, rating actions, audit and governance evidence | Identical collection checklist for that case and its candidate peers | P0 |
| D: reviewer/integrator | Independent checks of values, dates, units, identifiers and period length | Review each packet as it arrives; maintain a conflict list | P0 |
| Reference-data owner | Calendar, FX, independent default-study evidence and regulatory minima | Original source documents or a verified export with dates | P0; coordinate with Codex's public-source research |
| Independent sealed collector | Private cases and their preparation | Only the final file hash and case count sent to Codex | P0; separate private workflow |

Do not wait for every company before handing over data. Submit each reviewed company-year or disclosure batch immediately so validation and integration can proceed in parallel.

## 3. Tonight's collection order

1. **Start with cases and matching inputs.** Obtain the latest financials and classification/identity evidence that were public before each matching cutoff. Obtain a broad same-sector candidate roster and its assets/liabilities at that cutoff.
2. **Collect original report histories.** Cover the requested reporting years below, including earlier original reports or comparatives needed for lagged features. Seek at least the configured number of complete pre-event financial periods; a downloaded PDF alone is not complete coverage.
3. **Extend collection to eligible candidates.** Codex selects peers mechanically. Then finish the selected peers' financials and disclosure histories using exactly the same checklist as for cases.
4. **Complete shares, financial-sector inputs and soft signals.** Missing shares block market capitalisation. Unknown governance histories cannot be turned into negative signals.
5. **Review source timing and resolve gaps.** Hand over remaining missing fields honestly. Do not fill a spreadsheet just to make the acceptance check pass.
6. **Freeze only after validation.** Codex will create and commit the registration lock before scoring. No one should run final hold-out or sealed evaluation during collection.

## 4. Company assignments and date windows

These identifiers and event dates come from the reviewed output catalog. Matching and strict-snapshot dates are derived from the configured rules. **Evidence must be public strictly before a cutoff.** A report published on the cutoff date is excluded.

| Case | ISIN | Sector | Match: evidence before | Reports from year | Through year | Strict 4Q cutoff | Strict 8Q cutoff |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IL&FS Transportation Networks Ltd | INE975G01012 | infrastructure_development | 2015-09-28 | 2014 | 2018 | 2017-06-30 | 2016-06-30 |
| Dewan Housing Finance Corporation Ltd | INE202B01012 | housing_finance | 2016-06-04 | 2015 | 2019 | 2018-03-31 | 2017-03-31 |
| Jet Airways (India) Ltd | INE802G01018 | airlines | 2015-12-31 | 2014 | 2018 | 2017-12-31 | 2016-12-31 |
| Reliance Capital Ltd | INE013A01015 | nonbank_finance | 2016-09-09 | 2015 | 2019 | 2018-06-30 | 2017-06-30 |
| Reliance Home Finance Ltd | INE217K01011 | housing_finance | 2016-09-09 | 2015 | 2019 | 2018-06-30 | 2017-06-30 |
| Future Retail Ltd | INE752P01024 | retail | 2017-10-28 | 2016 | 2020 | 2019-09-30 | 2018-09-30 |
| Coffee Day Enterprises Ltd (CDEL) | INE335K01011 | diversified_nonfinancial | 2016-09-10 | 2015 | 2019 | 2018-06-30 | 2017-06-30 |
| Reliance Communications Ltd (RCom) | INE330H01018 | telecommunications | 2014-05-30 | 2013 | 2017 | 2016-03-31 | 2015-03-31 |
| Srei Infrastructure Finance Ltd | INE872A01014 | nonbank_finance | 2018-03-06 | 2017 | 2021 | 2019-12-31 | 2018-12-31 |
| Videocon Industries Ltd | INE703A01011 | consumer_electronics | 2015-06-06 | 2014 | 2018 | 2017-03-31 | 2016-03-31 |
| Jaypee Infratech Ltd | INE099J01015 | infrastructure_development | 2012-09-25 | 2011 | 2015 | 2014-06-30 | 2013-06-30 |
| Alok Industries Ltd | INE270A01011 | textiles | 2014-07-18 | 2013 | 2017 | 2016-06-30 | 2015-06-30 |

The reporting-year range is a collection guide, not permission to force every company into a March year-end. Record the actual financial period and its duration. Collect earlier supporting reports if the earliest scoring snapshot needs prior-year inputs. A later report's comparative column does not establish earlier availability.

Special attention:

- **Alok:** some reports/comparatives cover eighteen months. Do not enter those flows as twelve-month PAT, sales or CFO. Earlier balance sheets can still be collected with their true dates. FY2016 original statement evidence is now cached; FY2017 evidence uses the later sourced exchange dissemination date.
- **Videocon:** verify the actual reporting calendar and period duration before extracting any flow.
- **ITNL:** an attempted FY2016 annual-report link returned a cached 404. Find an actual original copy or exchange filing; do not rename the later comparative report as an earlier source.
- **Financial firms:** collect their financial-sector disclosures as well as ordinary accounts. A metric that is not applicable is not zero.

## 5. Financial statements: what A should collect

### Source packet

For each entity and reporting period, provide:

- Original standalone annual report or original exchange results PDF; consolidated statements as a separate basis.
- Exact public landing/download URL, local filename, and statement/notes page numbers.
- Actual financial-period end and the source report's own period end.
- Publication/dissemination evidence, if available. An auditor's signing date, board date or AGM date is not automatically the dissemination date.
- Printed denomination and whether each figure is standalone or consolidated.
- Period duration for every income/cash-flow column; flag restatements and nonstandard periods.

### Extract in this order

| Priority | Fields | Why |
|---|---|---|
| First: minimum nonfinancial core | `total_assets`, `total_liabilities`, `current_assets`, `current_liabilities`, `equity`, `retained_earnings`, `revenue`, `inventory`, `pat` | Financial-history acceptance and primary ratios |
| First: minimum financial-firm core | `total_assets`, `total_liabilities`, `equity`, `pat` | Financial-track history and classification checks |
| Next: scoring and cash evidence | `ebit`, `cash_and_st_investments`, `cfo`, `receivables`, `interest_expense`, `total_debt`, `st_borrowings`, `commercial_paper`, `lt_debt` | Market/accounting layer and liquidity inputs |
| Next: forensic inputs | `cogs`, `gross_profit`, `sga`, `depreciation`, `ppe_net`, `cwip`, `pbt`, `income_continuing`, `income_before_extraordinary`, `current_maturities_lt_debt`, `equity_issued` | Beneish, Piotroski and supporting diagnostics |
| Next: audit and group evidence | `auditor_opinion`, `going_concern_flag`, `caro_default_flag`, `caro_fraud_flag`, related-party loans/advances and revenue; consolidated debt | Hard triggers, explanations and additional checks |

Do not substitute borrowings for total liabilities, reserves for retained earnings, EBITDA for EBIT, aggregate finance costs for interest expense, or cash alone for cash plus short-term investments. The schema has separate `cash_and_cash_equivalents` and `finance_costs` fields for those narrower reported figures. If a total is not printed, leave it blank and send the component pages for review; do not improvise a value.

### Preferred target: field-level evidence

Use `financial_evidence.csv`-shaped handoffs. Each sourced field is reviewed independently, so a missing optional field does not quarantine an otherwise useful complete field. The wide `annual_financials.csv` format requires complete numeric rows to mark them verified and is less convenient for partial collection.

```csv
entity_id,fy_end,period_end,source_period_end,basis,field,numeric_value,text_value,unit,publication_kind,public_date,source_doc,source_page,date_is_imputed,needs_verification,is_synthetic
```

Field rules:

- `entity_id`: the sourced ISIN in the assignment table; candidate identities need their own source proof.
- `fy_end` and `period_end`: the actual financial period end, equal for these rows.
- `source_period_end`: the period end of the report actually used, including for older comparative values.
- `basis`: `standalone` or `consolidated`; never mix the two in one row.
- `numeric_value`: the number as printed in its declared unit. Use `text_value` only for a supported text field; a verified row contains exactly one of these values.
- `unit`: `INR`, `INR_lakh`, `INR_crore`, `INR_million`, `shares`, `shares_lakh`, `shares_million`, `shares_crore`, `flag` or `text`, as applicable. Codex performs the declared unit conversion.
- `publication_kind`: `annual_report` or `results`, according to the actual document containing that field.
- `public_date`: actual dissemination date when established. If it is unknown, leave it empty, set `date_is_imputed=1`, and retain the source reporting period. The pipeline applies the configured conservative lag; collectors should not invent an upload date.
- `source_doc`: the original source URL or an identified original document; provide the dissemination-evidence URL too when it is a different source.
- `source_page`: PDF page position, starting with the first page of the file. Note the printed page label separately if it differs.
- `needs_verification=0`: only after checking the value, unit, basis, period and source. Otherwise leave the unknown value blank and use `1`.
- `is_synthetic=0`: every handoff must contain real source evidence. No invented example rows or LLM estimates.

Record `auditor_opinion` as one of `clean`, `qualified`, `adverse`, `disclaimer`, using `unit=text`. Audit indicators and `equity_issued` use explicit binary evidence and `unit=flag`. A dash in a financial statement is not automatically a numeric zero.

## 6. Peer matching: what B should collect

The current rule requires at least three eligible peers per case, at least thirty distinct peers overall, with a target of thirty-six. At least a third of the distinct peers must qualify as stressed survivors. Shared peers count once toward the distinct-peer target.

For each case's **matching cutoff** in the table:

1. Provide a sourced historical sector/candidate roster, identifiers and financial/nonfinancial classification. A current sector label is insufficient if it was not established for that historical cutoff.
2. Provide candidate and focal-company total assets and total liabilities from reports public before the cutoff, using the same accounting basis and consistent units.
3. Include enough of the sector population to substantiate the leverage quartile. Do not define a purported sector-wide upper quartile using only three desired peers. Document any incomplete candidate-universe coverage.
4. Provide independent non-default evidence for the required survival window. An absent row in our event catalog does not prove survival.
5. Supply extra eligible candidates where shared sectors, overlap or missing evidence could prevent the distinct-peer/stressed-survivor quotas.

Codex computes asset distance, leverage cutoffs and final membership under the frozen rule. Do not choose peers based on whether their model scores improve recall.

Targets:

```csv
# entities.csv
entity_id,name,symbols,sector,is_financial,period_end,public_date,source_url,date_is_imputed,needs_verification,is_synthetic
# peer_survival.csv
entity_id,matched_to,nondefault_start,nondefault_through,period_end,public_date,source_url,date_is_imputed,needs_verification,is_synthetic
```

`nondefault_start` and `nondefault_through` must cover the independently checked window, including the configured forward survival horizon from the matching date. Include the source/search evidence and covered dates. If this cannot be established, keep the candidate pending.

Codex publishes `peers.csv` after mechanical selection. Its exact header is:

```csv
entity_id,name,symbols,sector,is_financial,matched_to,is_stressed_survivor,selection_rule_version,period_end,public_date,source_url,date_is_imputed,needs_verification,is_synthetic
```

## 7. Shares and disclosures: what C should collect

Collect these for cases **and** candidate/selected peers with the same effort and source checklist. Cover the pre-event lookback through the latest pre-event disclosure, with older anchors needed for year-over-year changes.

| Target | Collect | Important detail |
|---|---|---|
| `share_counts.csv` | Actual ending ordinary shares outstanding, period end, publication date, original filing | A weighted-average EPS denominator, current share count or paid-up capital alone is not a historical ending share count. Include relevant split/issue records. |
| `shareholding.csv` | Promoter holding and shares pledged **as a percent of promoter holdings** | Do not substitute pledge as a percent of total company shares. Include the prior-year quarter. |
| `rating_actions.csv` | Agency, instrument, action date, publication date, old/new symbols, watch/outlook, INC/default flags | Preserve long/short-term scales and exact instrument identity. Obtain earlier sub-investment-grade history, not only the final D release. |
| `governance_events.csv` | Auditor resignation, delayed results, CFO resignation, forensic audit order | Retain actual announcement date, original announcement and the defined event type. |
| `signal_coverage.csv` | Documented complete search windows for negative auditor-exit/delayed-filing signals | No-event search results are unknown unless coverage is established. A search performed today does not justify backdating its availability. |

The exact headers:

```csv
# share_counts.csv
entity_id,period_end,public_date,shares_outstanding,source_doc,date_is_imputed,needs_verification,is_synthetic
# shareholding.csv
entity_id,period_end,public_date,promoter_holding_pct,promoter_pledged_pct_of_promoter,source_url,date_is_imputed,needs_verification,is_synthetic
# rating_actions.csv
entity_id,agency,action_date,period_end,public_date,instrument,rating_from,rating_to,outlook,watch,inc_flag,is_default_grade,source_url,date_is_imputed,needs_verification,is_synthetic
# governance_events.csv
entity_id,event_type,announce_date,period_end,public_date,detail,source_url,date_is_imputed,needs_verification,is_synthetic
# signal_coverage.csv
entity_id,signal_name,coverage_start,coverage_end,period_end,public_date,source_url,date_is_imputed,needs_verification,is_synthetic
```

If collecting ending shares via field-level financial evidence, retain the printed share-count unit and source page. Tell Codex to populate the market-cap share-count input from that verified evidence; do not manually duplicate inconsistent conversions.

Do not record a negative flag just because a release does not mention it. Supply the complete coverage proof or keep the field unknown. Do not change the already human-verified event catalog: a D rating later cured before the final default is excluded under the global rule, and RCom's original CIRP commencement remains the reviewed date in the catalog.

## 8. Financial-sector and reference-data packets

### NBFC/HFC/CIC evidence

For every financial case and its financial peers, collect asset-quality, capital and ALM disclosures at each available quarter/half-year, plus the prior-year comparison:

```csv
entity_id,period_end,public_date,gnpa_pct,nnpa_pct,car_pct,nim_pct,cp_share_of_borrowings,st_liab_to_st_assets,loan_book_growth,source_doc,date_is_imputed,needs_verification,is_synthetic,car_minimum_pct
```

Use percentage points for `gnpa_pct`, `nnpa_pct`, `car_pct`, `nim_pct`, `car_minimum_pct`. Preserve ratio/fraction definitions for CP share, short-term liabilities/assets and loan-book growth, with a note of the printed units and denominator. Provide all periods consistently so Codex can normalize safely. The capital minimum must be applicable to the entity subtype and historical date; do not use today's rule for an earlier year. If a CIC does not report a metric, keep it missing and flag applicability for review.

### Reference sources

| Item | Needed evidence | Target |
|---|---|---|
| Trading calendar | Official annual calendars/holiday circulars, weekend trading rule and special-session circulars; suspension/listing evidence where relevant | `trading_calendar.csv`; Codex can build daily rows from complete documented rules |
| Historical identities | Contemporary original security-master/report proof of symbol, exchange code and ISIN | `security_crosswalk.csv`, `entities.csv` |
| INR/USD conversion | A dated official historical release and the date it was available; latest published observations before scoring cutoffs | `fx_rates.csv`; never silently use today's revised vintage as an old release |
| Independent horizon priors | Original CRA default study with one-/two-year aggregate rates or the counts/weights needed to establish them; population definition, period, publication date and pages | Source packet for model review; do not calculate priors from our selected cases/peers |
| Corporate groups | Dated ownership/group evidence and coverage of the relevant roster, including substantiated singleton status | `groups.csv`; lower priority than the core financial/peer packet |

```csv
# trading_calendar.csv
entity_id,period_end,public_date,is_trading_day,source_url,date_is_imputed,needs_verification,is_synthetic
# security_crosswalk.csv
entity_id,exchange,exchange_code,period_end,public_date,source_url,date_is_imputed,needs_verification,is_synthetic
# fx_rates.csv
entity_id,period_end,public_date,inr_per_usd,source_url,date_is_imputed,needs_verification,is_synthetic
# groups.csv
entity_id,group_id,group_name,membership_complete,period_end,public_date,source_url,date_is_imputed,needs_verification,is_synthetic
```

For a group row, `membership_complete=1` certifies a documented complete roster; `0` records known partial coverage. A single collected member is not proof that the company has no siblings. Do not infer an ISIN from a similar name or apply a later security mapping to an earlier cutoff without contemporaneous proof.

Do not manually collect daily equity prices or compute model scores, thresholds, weights or metrics. Codex is handling public market archives and model implementation. If a source is blocked or unavailable, hand over the original document/official download rather than a copied unsourced figure.

## 9. Handoff convention

Use a separate ordinary intake folder per owner under `data/raw/manual/<owner>/` so parallel CSV edits do not collide. Keep the exact target CSV headers above and use descriptive filenames. These are intake copies; Codex merges reviewed rows into the authoritative `data/manual/` inputs.

Each ordinary packet should include:

- Original PDFs/CSVs, unchanged.
- Source URLs and which local file each URL identifies.
- CSV rows, or statement pages with an extraction checklist if transcription would slow collection.
- Review notes with entity, period, basis, page, denomination, publication evidence and unresolved ambiguities.
- Collector and reviewer names in a short handoff note. Keep project notes under `docs/intake/`; never place sealed notes there.

Check the existing cache/catalog first. Codex will register manual downloads through the cached downloader, preserve immutable bytes and produce receipts. Do not commit raw source files, cookies, credentials, `.venv/` or protected sealed material.

## 10. Review and acceptance checklist

- [ ] Identity, financial classification and sector are sourced for the relevant historical cutoff.
- [ ] Financial values agree with the original page; units and accounting basis are consistent.
- [ ] Annual flows are actually twelve-month flows; restatements/nonstandard periods are identified.
- [ ] Actual dissemination dates are supported, or unknown dates are explicitly marked for the configured conservative lag.
- [ ] Unknown values remain blank with `needs_verification=1`; no dash, absence or missing search is converted into zero.
- [ ] Same collection checklist is completed for cases and peers.
- [ ] Candidate-pool scope and survival coverage support the peer-selection rule.
- [ ] Every real row has `is_synthetic=0` and source provenance.
- [ ] No protected case identities or files enter ordinary handoffs or chat.

Codex will run manual-schema validation, accounting identities, financial/market coverage and peer-selection checks. A schema-valid partial packet is useful, but it does not establish complete panel acceptance. Do not mark missing evidence complete to reach a deadline.

## 11. Independent sealed collector

Follow [SEALED_INPUT_CONTRACT.md](SEALED_INPUT_CONTRACT.md) in a private workflow. Prepare features with the published feature-building code in a separate private copy of the project; do not fit or score models while preparing the envelope. Include the full historical ranking cohort and the private case marker, preserving unknown inputs.

Place the prepared artifact and private sources only in the protected location specified by the contract. Provide **only the SHA-256 and distinct case count** to the modeller. Do not send names, event dates, private screenshots or file lists. The modeller will not inspect the protected directory before the explicit once-only final boundary.

## 12. First handoff message to send

For an ordinary packet, send: owner/workstream, company IDs, periods completed, intake folder path, sources needing review, and remaining missing items. For sealed work, send only the artifact hash and case count. No one needs to run training, replay or final evaluation commands as part of collection.
