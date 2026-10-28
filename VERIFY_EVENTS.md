# Event verification checklist

Verified by the user on 2026-10-28 (all 22 rows ticked). Prepared 2026-10-28 from original documents (rating-agency releases, IBBI Form A notices, company exchange filings). Every date below was read from the linked document itself, not from news articles or memory. The ticked rows were imported into `data/manual/events.csv` on 2026-10-28, with component publication dates in `data/manual/event_evidence.csv`.

**How to verify a row:** open the link, find the quoted text, and check that the date matches. Then change `[ ]` to `[x]`. If anything is wrong, write `WRONG:` and a note at the end of the row. When you're done, tell Claude or Codex, and only the `[x]` rows get copied into `events.csv` with `needs_verification=0`.

"Public date" means the date the document was published. The model is only allowed to know about an event from that date onward.

Coverage note: "first D" means the earliest D found in this search, not a proven earliest across every agency. Other agencies (CRISIL, India Ratings, Brickwork) may have acted earlier for some companies; that limitation stays recorded until someone checks.

---

## 1. ITNL: IL&FS Transportation Networks Ltd

- [x] **First D rating: 2018-09-28 (CARE).** Public date 2018-09-28.
  Quote: "The revision in the rating of IL&FS Transportation Networks Limited (ITNL) factors in the delay in debt servicing." Bank facilities and NCDs revised to CARE D from CARE BB.
  https://www.careratings.com/upload/CompanyFiles/PR/IL&FS%20Transportation%20Networks%20Limited-09-28-2018.pdf
  Watch out: CARE's release of 2018-09-26 rates ITNL at **BB**, not D. The D in that release is for the parent, IL&FS. Some news summaries get this wrong.
- Payment default date: not stated in the release. Left blank.
- Insolvency (CIRP) date: not looked up.

## 2. DHFL: Dewan Housing Finance Corporation Ltd

- [x] **First D rating: 2019-06-05 (ICRA, ₹850 cr commercial paper).** Public date 2019-06-05.
  Quote: "...delays in meeting scheduled debt obligation on June 04, 2019."
  https://www.icra.in/Rating/ShowRationalReportFilePdfViewer/81083
- [x] **Payment default: 2019-06-04** (from the same ICRA release). Public date 2019-06-05.
- [x] **CIRP commencement: 2019-12-03.** Public date 2019-12-04 (IBBI announcement date).
  Quote: "...ordered the commencement of a corporate insolvency resolution process of DHFL on December 3, 2019."
  https://ibbi.gov.in//uploads/announcement/0cc175b9c0f1b6a831c399e269772661.pdf

## 3. Jet Airways (India) Ltd

- [x] **D rating: 2019-01-02 (ICRA).** Public date 2019-01-02.
  Quote: "The ratings downgrade considers the delays by the company in the payment of the interest and principal installment due on December 31, 2018 due to cash flow mismatches."
  https://www.icra.in/Rating/ShowRationalReportFilePdf/76249
- [x] **Payment default: 2018-12-31** (from the same ICRA release). Public date 2019-01-02.
- CIRP: already in `events.csv` (2019-06-20, sourced by Codex).
- **Decision recorded (human, 2026-10-28):** exclude any D later cured back to investment/normal grade before the final default, for every company. Jet uses the 2019 ICRA D; the earlier cured 2014 episode does not count. The earliest ticked payment default still determines Jet's event date. See `DECISIONS.md`; no Indian results were seen before this decision.

## 4. Reliance Capital Ltd

- [x] **First D rating: 2019-09-20 (CARE).** Public date 2019-09-20.
  Quote: "The rating revision takes into account the recent instance of delay in servicing of coupon on several non-convertible debentures by the company. The coupon was subsequently serviced with a delay of one working day."
  https://www.careratings.com/upload/CompanyFiles/PR/Reliance%20Capital%20Limited-09-20-2019.pdf
- [x] **Payment default: 2019-09-09** (coupon due date; same CARE release: "Coupon payments of certain Non-Convertible Debentures (NCDs) of RCL were due on September 09, 2019"). Public date 2019-09-20.
  Note: the company disputed this, blaming a bank-server glitch.
- [x] **CIRP commencement: 2021-12-06.** Public date 2021-12-07 (Form A date).
  Quote: "...has ordered the commencement of a corporate insolvency resolution process of the Reliance Capital Limited by its order dated December 06, 2021."
  https://ibbi.gov.in//uploads/announcement/9fe33957448ce5c91fe351847787b5d8.pdf

## 5. Reliance Home Finance Ltd

- [x] **First D rating: 2019-09-12 (CARE).** Public date 2019-09-12.
  Quote: "The rating revision takes into account the recent instance of delay in servicing of principal on one of the non-convertible debentures by the company."
  https://www.careratings.com/upload/CompanyFiles/PR/Reliance%20Home%20Finance%20Limited-09-12-2019.pdf
- [x] **Payment default: 2019-09-09** (same release: "RHFL's Non-Convertible Debentures (NCDs) were due for redemption on September 09, 2019 ... RHFL has defaulted on the payment of the redemption principal"). Public date 2019-09-12.
- CIRP: IBBI lists an insolvency announcement for RHFL dated **2025-09-18** (applicant: Invent Assets Securitisation and Reconstruction). The notice is a 14-page scan, so I did **not** read the commencement date. Left blank; needs someone to open it.
  https://ibbi.gov.in//uploads/announcement/2025-09-18-164852-buca3-f4cbe6a7078b489ec4b4a7537c528858.pdf

## 6. Future Retail Ltd

- [x] **First D rating: 2020-10-28 (Acuité).** Public date 2020-10-28.
  Quote: "The current rating action is on account of the default in redemption of Commercial Paper."
  https://www.acuite.in/documents/ratings/revised/17272-RR-20201028.pdf
- Payment default date: the release doesn't give the CP due date. Left blank.
- [x] **CIRP commencement: 2022-07-20.** Public date 2022-07-23 (IBBI announcement date).
  Quote: "Insolvency commencement date in respect of corporate debtor July 20, 2022"
  https://ibbi.gov.in//uploads/announcement/41f4dc1e7ba660f9b05a52a47f748639.pdf

## 7. Coffee Day Enterprises Ltd (CDEL)

- [x] **First D rating: 2019-09-10 (ICRA, ₹315 cr term loans).** Public date 2019-09-10.
  Quote: "The rating action follows the delay in debt servicing by CDEL's flagship subsidiary – Coffee Day Global Limited and Sical group of companies."
  https://www.icra.in/Rating/ShowRationalReportFilePdf/88300
  Note: the trigger was default by **subsidiaries**, not CDEL itself. That's still a D on CDEL, but worth knowing.
- Payment default by CDEL itself: not found. Left blank.
- [x] **CIRP commencement: 2024-08-08.** Public date 2024-08-10 (IBBI announcement date).
  Quote: "...commencement of a corporate insolvency resolution process of the Coffee Day Enterprises Limited on 08 August 2024."
  https://ibbi.gov.in//uploads/announcement/6eac373d5a284646a90977c094409bde.pdf

## 8. Reliance Communications Ltd (RCom)

- [x] **First D rating: 2017-05-30 (ICRA).** Public date 2017-05-30.
  Quote: "The revision in ratings takes into consideration the delays in debt servicing by the Group given its weak internal cash flow generation as against sizeable debt servicing obligations."
  https://www.icra.in/Rating/GetRationalReportFilePdf?Id=35656
- Payment default date: not stated in the release. Left blank.
- [x] **CIRP commencement: 2018-05-15.** Public date 2018-05-21 (IBBI announcement date of the first Form A).
  From the re-issued Form A of 2019-05-07: "15 May 2018. The Hon'ble National Company Law Appellate Tribunal vide its Order dated May 30, 2018 had stayed the Corporate Insolvency Resolution Process ... and by its order dated April 30, 2019 had vacated the stay."
  https://ibbi.gov.in//webadmin/pdf/announcement/2019/May/RELIANCE%20COMMUNICATION%2013-05-19_2019-05-13%2012:06:36.pdf
  Original 2018 notice: https://ibbi.gov.in//webadmin/pdf/announcement/2018/May/Form%20A-%20Reliance%20Communication_2018-05-28%2015:22:53.pdf

## 9. Srei Infrastructure Finance Ltd

- [x] **First D rating: 2021-03-06 (CARE).** Public date 2021-03-06.
  From Srei's own exchange filing of 2021-03-06: "CARE Ratings Limited (CARE) has revised the ratings assigned to Long Term and Short Term Bank facilities ... to 'CARE D (Single D)'." The company called it "blatantly wrong, misleading and baseless".
  https://www.srei.com/storage/app/uploads/public/604/5d1/879/6045d187973a9031381410.pdf
  CARE's own release (linked from the filing): https://www.careratings.com/upload/CompanyFiles/PR/06032021013323_Srei_Infrastructure_Finance_Limited.pdf
- Payment default date: not found. Left blank.
- [x] **CIRP commencement: 2021-10-08.** Public date 2021-10-11 (Form A date).
  Quote: "Insolvency commencement date ... October 8, 2021 vide order no. C.P. (IB)-295/KB/2021"
  https://ibbi.gov.in//uploads/announcement/b79a45775818790cf9e6b93af65b3a7b.pdf

## 10. Videocon Industries Ltd

- First D rating: **none found.** CARE appears to have suspended its rating in 2016 instead of moving it to D. Left blank.
- Payment default date: not found. Left blank.
- [x] **CIRP commencement: 2018-06-06.** Public date 2018-06-09 (Form A date).
  Quote: "...the National Company Law Tribunal has ordered the commencement of a corporate insolvency resolution process against VIDEOCON INDUSTRIES LIMITED on 6th June 2018"
  https://ibbi.gov.in//webadmin/pdf/announcement/2018/Jun/Form%20A-%20Videocon%20Industries%20Ltd._2018-06-14%2016:43:23.pdf

## 11. Jaypee Infratech Ltd

- [x] **First D rating: 2015-09-25 (CARE).** Public date 2015-09-25.
  Quote: "Long-term Bank Facilities 6,550 CARE D [Single D] Revised from CARE BB" ... "resulting in weak liquidity position and ongoing delays in debt servicing."
  https://www.careratings.com/upload/CompanyFiles/PR/Jaypee%20Infratech%20Limited-09-25-2015.pdf
  This is almost **two years before** the CIRP already in `events.csv` (2017-08-09).
- Payment default date: release says "ongoing delays" but gives no date. Left blank.
- CIRP: already in `events.csv` (sourced by Codex).

## 12. Alok Industries Ltd

- First D rating: **none found.** Left blank.
- Payment default date: not found. Left blank.
- [x] **CIRP commencement: 2017-07-18.** Public date 2017-07-19 (Form A date).
  Quote: "...the National Company Law Tribunal, Ahmedabad Bench, has ordered the commencement of a corporate insolvency resolution process against Alok Industries Limited on 18th July, 2017."
  https://ibbi.gov.in//webadmin/pdf/announcement/2017/Jul/IRP_Form%20A-%20Alok%20Industries.pdf

---

## Summary

| Company | First D | Payment default | CIRP |
|---|---|---|---|
| ITNL | 2018-09-28 | – | not looked up |
| DHFL | 2019-06-05 | 2019-06-04 | 2019-12-03 |
| Jet Airways | 2019-01-02 (cured 2014 D excluded) | 2018-12-31 | in csv |
| Reliance Capital | 2019-09-20 | 2019-09-09 | 2021-12-06 |
| Reliance Home Finance | 2019-09-12 | 2019-09-09 | 2025 notice unread |
| Future Retail | 2020-10-28 | – | 2022-07-20 |
| Coffee Day Ent. | 2019-09-10 | – | 2024-08-08 |
| RCom | 2017-05-30 | – | 2018-05-15 |
| Srei Infra | 2021-03-06 | – | 2021-10-08 |
| Videocon | – | – | 2018-06-06 |
| Jaypee Infratech | 2015-09-25 | – | in csv |
| Alok Industries | – | – | 2017-07-18 |

Every company has at least one sourced date, so all 12 can count as verified events once you tick their rows. The pipeline needs at least 10.

## Notes for whoever writes these into `events.csv`

- All 21 distinct linked PDFs have been registered through the cached downloader with receipts under gitignored `data/raw/`. The three human-downloaded originals are retained under `data/raw/manual/`.
- `event_date` = the earliest ticked date among the three fields. Don't pick a later one.
- Record the Jet Airways 2014 decision, and the RCom stayed-then-restarted CIRP (2018-05-15 kept as the commencement date), in `DECISIONS.md`.
- Decisions recorded: the cured-D exclusion applies to every company; Jet uses the 2019 D and its earlier ticked payment default, and RCom retains original commencement. Missing event fields and classifications remain blank.
