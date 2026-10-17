# PEN-Plus regional dashboard: audit and refinement plan (version 2, 17 Oct 2026)

Site audited: build of 16 Oct 2026 (`f60a07b`), all six screens.
Data audited: the team's ICPPA country extraction (`PEN-Plus_country_data_ICPPA2026.xlsx`, 28 July 2026),
`PEN_PLUS_MONITORING.xlsx`, the five ICPPA 2026 slide decks (1,026 slides), the new national quarterly reporting
tool, and the South Sudan NCD data-system assessment.

**Framing.** This is the PEN-Plus dashboard. The ICPPA 2026 country presentations are the baseline from our own
records, the first data the dashboard can show until second-round quarterly returns arrive. They are
country-reported, not validated returns, and every screen must say so.

## 1. Root causes of what the dashboard shows today

| Symptom on the site | Root cause | Fix |
|---|---|---|
| Implementation phases: "31 countries not yet started", "0 with phase data" | `seed_history.from_monitoring_phases` reads the country from column index 3; the country is in index 2 (column C). It matches 0 of 20 countries. Tested: with index 2 it reads 18; the two Congos still fail because the workbook writes "Democratic Republic of Congo" and "Congo, Republic of". | Fix the index; add those names (and "KEN Kenya", used on another sheet) to the country aliases; publish the phase from `implementation_phase_reconciliation.csv`. |
| Patients ever enrolled 13,222; Uganda 2,241, Burkina Faso 3,902, DRC 570 | The extraction puts Uganda's severe HTN (15), Burkina Faso's "HTA" (3,402) and DRC's "HTA" (563) in the *Severe hypertension* column, and `common.TRACERS` still counts `severe_htn` in the sentinel total. Severe hypertension was dropped as a priority condition in Sept 2026. | Take `severe_htn` out of the sentinel total (keep it under other conditions). Uganda becomes 2,226, Burkina Faso SCD 500, DRC SCD 7. |
| Zimbabwe 4,590 | Taken as-is from the 2025 scale-up district table, where T1D = 3,201 in 8 districts, implausible for type 1 alone. | Hold with a High query until MoHCC confirms the case definition. |
| Facility counts wrong in 10 countries (e.g. Zimbabwe 1, Sierra Leone 3, Ghana 3, Kenya 0) | `from_icppa` builds the facility list by splitting "Site or district names" on ";". Zimbabwe's names are separated by commas (1 site); "planned: Kambia and Moyamba" becomes one site; Ghana's free text becomes 3. | Load facilities from `02_data/facility_register.csv` instead (43 facilities and pilot sites, with status). |
| No figure for Tanzania, Ethiopia, Mozambique, Zambia, Cameroon patients | These are in `Other_Reported_Figures` (no year breakdown), which the pipeline never reads. | Load the new `Load_Map_Other_Figures` sheet (machine-readable: indicator, condition, value, value type, as-of, load Y/N). |
| No figure for Kenya, Malawi, Nigeria | The first extraction did not have the Day 1 and Day 2 Mikumi room decks. | Added in v2 (rows highlighted yellow). Kenya cumulative 559; Malawi enrolment held (series type unclear); Nigeria flagship site. |
| Health workers trained "Not reported" everywhere | `Staff_Trained_by_Year` is read but no indicator is built from it. | Build 3.3 (historical) from it and from the load map. |
| Overview: "20 of 31 countries have published at least one figure" next to "6 of 31 reporting" | "Published" counts countries with any return row, even all-null. | Count a country only for a non-null value; show coverage per indicator. |
| Data quality: "0 below 80%", "0 open queries", every row "Accepted" | Nothing is tested; the form tables those columns came from no longer exist in the new tool. | Rebuild to `04_data_quality/DATA_QUALITY_SPEC.md`; seed 28 queries from `02_data/data_queries.csv`. |

## 2. Does it fit the current phase of PEN-Plus?
Partly. The structure (31 countries, two HCT rounds, focus areas, quarterly rhythm) matches the second round.
What doesn't fit yet:
- **Conditions**: the sentinel set is T1D, SCD and RHD; severe hypertension must leave every sentinel total.
- **Indicator definitions** must follow the new tool: 2.5 = all PEN-Plus patients (country-defined conditions included);
  2.6 = sentinel cohort (ever, new, active); HMIS integration is **5.2** (`03_reporting_form/form_diff_repo_v3_vs_new.diff`).
- **Implementation phases**: the official map at ICPPA places Rwanda in phase 5, 15 countries in phase 4, Congo,
  Lesotho and Niger in phase 3, Nigeria in phase 2. The monitoring workbook agrees for 15 of 20 and disagrees for
  Ghana, Kenya, Mozambique, Niger and Nigeria (query Q-PHS-01).
- **Second-round countries** (11): no data yet. Show "no return yet", never "not started" and never omitted.
- **Regional headline**: the WHO AFRO slides say 170,000+ patients and 120 district hospitals (Day 2) and "Several"
  patients (Day 1); the sum of country figures is far lower. Publish none until one figure and its scope are agreed (Q-REG-01).

## 3. Facility names and geolocation
- The public build hides facility names. These are public hospitals named at a public conference; the suppression
  rule should protect small patient counts, not facility identity. **Team decision** before Claude Code changes it.
- `facility_register.csv`: 43 rows (34 confirmed names), region, district, partner, status, conditions, the patient
  figure printed for the facility where one exists (Zambia's 5 hospitals, Kondoa, Karatu, Koidu, Pujehun, J.J. Dossen), and the source slide.
- Coordinates: run `02_data/GEOCODING_PROTOCOL.md` (OpenStreetMap, strict matching, human review). Longer term,
  ask for GPS or the DHIS2 org-unit UID in Annex A of the reporting tool.

## 4. Screens
- **Overview**: split patients into *sentinel conditions* and *all PEN-Plus conditions*; health workers trained from the
  baseline with its coverage; banner "Baseline from country presentations at ICPPA 2026, not yet validated quarterly returns".
- **Indicator detail**: new-tool definitions; value type shown (ever enrolled / active / as of); trend lines only where a
  real series exists (Sierra Leone, Uganda, Liberia, Kenya; Rwanda as *active*).
- **Country profile**: country map and coat of arms (`05_design/COUNTRY_ASSETS.md`), facility list with status, every figure
  with its source slide, open queries.
- **Implementation phases**: phase per country from the reconciliation file, step grid from the monitoring workbook, disagreements flagged.
- **Data quality**: rebuilt (spec in `04_data_quality/`).
- **Facilities**: names, status, partner, map from checked coordinates.

## 5. The reporting tool itself
- The printed 2.6 retention formula divides by the patients *no longer* in care (it can give 350%). Correct it before the
  LimeSurvey version goes out; the pipeline must compute retention itself.
- Add GPS / DHIS2 UID to Annex A.

## 6. Before senior leadership sees it
Send `02_data/data_queries.csv` (28 queries, 7 High) to the WHO Country Offices and NCD focal points, and get the
High ones answered. Until then the dashboard shows baseline figures with their provenance, not programme results.
