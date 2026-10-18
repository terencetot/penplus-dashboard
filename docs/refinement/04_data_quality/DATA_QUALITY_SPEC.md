# Data quality screen: diagnosis and rebuild specification

The screen must answer one question: **how much of this can be trusted?**
Today it cannot, and in places it answers the opposite of the truth.

## 1. What is wrong with the current screen (build of 16 Oct 2026)

| # | What the screen shows | Why it is wrong | Severity |
|---|---|---|---|
| 1 | "0 countries below 80%" | Completeness is NR for every country. Zero below threshold reads as "all good"; the truth is "not measurable". | High |
| 2 | "0 open queries", "No open queries" | The ICPPA evidence alone raises 28 queries (`02_data/data_queries.csv`), 7 of them High. The register is empty because nothing is tested, not because nothing is wrong. | High |
| 3 | Every row has the status "Accepted" | Historical rows were never validated. "Accepted" certifies a check that did not happen. | High |
| 4 | Columns "Completeness", "Returns on time", "90-day LTFU rule applied", "Confidence: patients" | All are NR everywhere. Four of them depend on form tables that **no longer exist** in the new reporting tool (see section 2). | High |
| 5 | Only 20 countries listed | The 11 second-round countries are missing. CLAUDE.md rule 10: a country is never omitted. | Medium |
| 6 | Two panels with the same title, one of them an empty chart | Duplicate and empty. | Low |
| 7 | "Historical" on every row as a column | Provenance is useful, but as the only populated column it dominates the table. | Low |

## 2. The new reporting tool changes what can be measured

Compared with the v3 form the pipeline parses (`docs/Phase_2_PEN-Plus_Reporting_Tools.docx`), the new
national quarterly tool (`03_reporting_form/`) has **removed**:

- the "Data quality and reconciliation" table (Annex A vs 2.3, patients vs 2.5/2.6, mentorship vs 3.4, definition changes, corrections);
- the "Confidence and means of verification" table (High/Medium/Low per domain);
- the reporting completeness % and timeliness % lines, and data collection frequency;
- the supplementary patient movement table (LTFU, transferred out, stopped, died);
- the section 7 progress summary table.

It has **renumbered** HMIS integration from 5.1 to **5.2** (5.1 no longer exists on the form), redefined
**2.5** as *all PEN-Plus patients ever enrolled, including country-defined conditions* (one row) and
**2.6** as the *sentinel T1D / SCD / RHD* cohort with ever enrolled, new, active and retention.

So the data quality screen must be rebuilt on what the form still provides plus checks the pipeline
computes itself. Self-declared confidence and reconciliation are gone; **computed checks replace them.**

Measurable from the new form:
- Section 0 "National context and reporting completeness": facilities expected, complete, partial, no return.
- Section 0 "Date completed" against the quarter end, which gives timeliness.
- Annex A facility register (status Active / Suspended / Closed / Not yet initiated).
- Every indicator table, for arithmetic and consistency checks.

## 3. Problem to fix in the form itself (tell the M&E focal point)

Indicator 2.6 prints: *Retention % = [active in care − newly enrolled] ÷ [ever enrolled − active in care] × 100*.
The denominator is the number of patients **no longer** in care, so the result is not a proportion
(e.g. ever 100, active 80, new 10 gives 70 ÷ 20 = 350%). The pipeline must **not** read a country-entered
retention %. It should compute:

    retention_approx = (active_in_care − newly_enrolled_this_quarter) ÷ (ever_enrolled − newly_enrolled_this_quarter)

labelled "approximate retention (excludes patients enrolled this quarter)", and the form should be corrected
before the LimeSurvey version goes out.

Also recommended for the form: add **GPS latitude / longitude** (or a national facility code / DHIS2 org unit UID)
to Annex A so facilities can be mapped without geocoding by name.

## 4. The rebuilt screen

Order on the page, top to bottom:

### 4.1 KPI row (each card carries its n of N)
1. **Countries with a validated form return for the latest quarter**: n / 31 (today 0 / 31; say so plainly).
2. **Figures held from publication**: count of indicator values with an open High query.
3. **Open queries**: total, with High / Medium / Low split.
4. **Indicators with country coverage ≥ 80%**: n / 16.

### 4.2 Evidence provenance (all 31 countries, one row each)
Columns: country, cohort (first / second HCT round), evidence source (*form return* / *ICPPA 2026 historical* / *none yet*),
latest period, value types used (flow, cumulative, active, point-in-time), open queries (count, highest severity).
Status vocabulary for the row: **Validated**, **Not validated (historical evidence)**, **Held (open High query)**, **No return yet**.
Never "Accepted" for something that was not tested.

### 4.3 Coverage matrix (countries × the 16 indicators)
Cell states: value present · held · not reported. Use shape and text, not colour alone (CLAUDE.md rule 9).
This replaces the empty completeness chart and shows at a glance that, for example, health workers trained has historical evidence in 12 countries but no form return yet.

### 4.4 Validation checks (run by `validate.py` on every return and on the historical evidence)
One row per rule with counts *passed / failed / not testable*. Clicking a rule lists the failing country-periods.

| Rule | Check | Severity if failed |
|---|---|---|
| R01 | Section 0: complete + partial + no return = facilities expected | High |
| R02 | Annex A facilities with status Active = indicator 2.3 "active during period" | High |
| R03 | 2.3 active ≤ 2.3 initiated (cumulative) | High |
| R04 | 2.6 per condition: newly enrolled ≤ ever enrolled; active ≤ ever enrolled | High |
| R05 | 2.6 sentinel total ≤ 2.5 total (sentinel is a subset of all PEN-Plus patients) | High |
| R06 | Cumulative stocks (2.3 initiated, 2.5, 2.6 ever enrolled, 3.1, 3.2) never decrease between consecutive quarters | High |
| R07 | 3.1, 3.2, 3.3: female + male + other = total; 3.3 year to date ≥ this quarter | Medium |
| R08 | 3.4 numerator ≤ denominator, and denominator = 2.3 active | Medium |
| R09 | 2.4: meeting criteria ≤ assessed ≤ 2.3 initiated; printed % = computed % (± 1 point) | Medium |
| R10 | Tracer stock-out facility counts ≤ 2.3 active | Medium |
| R11 | Every "Yes" on 1.1, 1.2, 1.3, 2.1 and 4.1 carries a document title | Medium |
| R12 | Year achieved within 2015-2029 and not after the reporting year | Low |
| R13 | Consent safeguard answered "Yes" whenever any patient-featuring product is reported in 6.1 | Medium |
| R14 | Quarter-on-quarter change in 2.5 above +100% or any decrease: flag for review | Low |
| R15 | Plausibility: T1D patients per active facility above a configurable ceiling (default 300) | Medium |
| R16 | Timeliness: date completed ≤ quarter end + 30 days | Low |
| R17 | Cross-source: a form value differs by more than 10% from the ICPPA historical value for the same country and period | Medium |

A High failure sets `verdict = 'hold'`; held figures stay out of every published total and are listed on this screen
(the mechanism already exists in `transform.py`).

### 4.5 Query register
Seed it from `02_data/data_queries.csv` (28 queries) and append pipeline findings.
Columns: ID, country, indicator, severity, issue, evidence (deck + page or rule), action, status, date opened.
Filters by severity, country and status. CSV export.

### 4.6 Country data-system readiness (new panel)
From the country NCD data-system assessment (first one received: South Sudan, 14 Oct 2026,
`country_data_system_assessment_SSD.csv`). One card per country that has answered: HMIS platform, EMR at district
hospitals, standard NCD register, unique patient ID, where data are entered, can the channel carry a quarterly report,
can indicators be added, main constraint. Countries without an assessment are listed as "assessment not yet received".
Never publish respondent names or e-mail addresses.

## 5. Acceptance criteria
- Not one card reads "0" when the truth is "not measurable".
- The 31 countries always appear.
- Loading the corrected extraction produces at least the 28 seeded queries, and the figures under High queries are absent from the regional totals.
- A test return with an arithmetic error (e.g. active > ever enrolled) appears as a failed R04 and as a held figure.
