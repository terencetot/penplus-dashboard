# PEN-Plus regional dashboard — data model and build contract

> Transcribed from `PEN-Plus_Dashboard_Data_Model.xlsx` for readability and
> diffability in version control. The original workbook is kept alongside
> this file; where the two differ, the workbook is authoritative.

Companion to `docs/specification.md`. Defines the tables the pipeline
produces, the fields the dashboard reads, and the rules that govern how a
value is displayed.

**Grain vocabulary:** *stock* = a value taken at a point in time, never
summed across periods. *flow* = a value covering a period, summed across
periods. *status* = a state that persists until it changes.

## 1. Tables

| Table | Grain | Primary key | Source in the form | Nature | Notes |
|---|---|---|---|---|---|
| `dim_country` | One row per country | `iso3` | Section 1 country list | reference | 31 countries; carries phase 1 or phase 2 cohort |
| `dim_period` | One row per reporting period | `period_id` | Section 1 rhythm and period | reference | Month and quarter both resolve to a quarter for regional aggregation |
| `dim_facility` | One row per facility, permanent | `facility_id` | Annex A block 1 | reference | Identifier assigned once by the Regional Office and never reused |
| `dim_indicator` | One row per indicator | `indicator_code` | Annex B and the traceability workbook | reference | Holds the definition, formula, direction and milestone |
| `fact_return` | One row per country and period | `iso3`, `period_id` | Section 1 and the validation step | event | Verdict of the quality control: accepted, query, hold |
| `fact_patient_stock` | country, period, condition | `iso3`, `period_id`, `condition` | Section 2.1 | stock | Ever enrolled and active at period end |
| `fact_patient_flow` | country, period, condition | `iso3`, `period_id`, `condition` | Section 2.2 | flow | New, lost, transferred, stopped, died |
| `fact_patient_age` | country, period, condition, age band | `iso3`, `period_id`, `condition`, `age_band` | Section 2 age table | stock | Must reconcile with active in `fact_patient_stock` |
| `fact_workforce` | country, period, cadre | `iso3`, `period_id`, `cadre` | Section 3 | flow and stock | Trained is a flow; working at a site is a stock |
| `fact_supply` | country, period, item | `iso3`, `period_id`, `item` | Section 4 | status and count | Availability class and facilities with a stock-out |
| `fact_service` | country, period, measure | `iso3`, `period_id`, `measure` | Section 5.1 and 5.2 | flow | Section 5.2 measures are nullable by design |
| `fact_assumption` | country, period, assumption | `iso3`, `period_id`, `assumption` | Section 5 | status | Holding, under strain, not holding, not assessed |
| `fact_governance` | country, milestone | `iso3`, `milestone_code` | Section 6.1 | status | Carries the achievement date and the evidencing document title |
| `fact_facility_period` | facility, period | `facility_id`, `period_id` | Annex A block 2 | mixed | Return received, ever enrolled, active, mentorship months, quality score, readiness class |
| `fact_quality` | country, period | `iso3`, `period_id` | Section 1 completeness and Section 7 confidence | derived | Completeness share, confidence class per indicator group, definition compliance |
| `gold_indicator` | country, period, indicator, disaggregation | `iso3`, `period_id`, `indicator_code`, `disagg` | Computed | derived | Numerator, denominator, value, completeness flag, suppression flag |

## 2. Fields

| Table | Field | Type | Allowed values or range | Nullable | Meaning |
|---|---|---|---|---|---|
| `dim_country` | `iso3` | text(3) | ISO 3166-1 alpha-3 | no | Country code |
| `dim_country` | `cohort` | enum | `phase_1`, `phase_2` | no | Determines whether the country is pooled in the first year |
| `dim_period` | `period_id` | text | `YYYY-Qn` or `YYYY-MM` | no | Reporting period |
| `dim_period` | `quarter_id` | text | `YYYY-Qn` | no | Quarter a monthly period rolls up to |
| `dim_period` | `days_in_period` | integer | 28 to 92 | no | Taken from Section 1; caps period-bounded counts |
| `dim_facility` | `facility_id` | text | `ISO3-nnnn` | no | Permanent; never reused, never renamed |
| `dim_facility` | `project_supported` | enum | `yes`, `no`, `partial` | no | Basis of every attribution statement |
| `dim_facility` | `status` | enum | `operational`, `started_this_period`, `under_preparation`, `suspended`, `closed` | no | Drives indicator 2.3 |
| `fact_return` | `verdict` | enum | `accepted`, `query`, `hold` | no | A hold never reaches `gold_indicator` |
| `fact_return` | `received_at` | date | – | no | Used for timeliness |
| `fact_patient_stock` | `condition` | enum | `t1d`, `scd`, `rhd`, `severe_htn`, `other_reported` | no | Four tracers plus the declared other line |
| `fact_patient_stock` | `ever_enrolled` | integer or null | 0 or more, null means NR | yes | Cumulative; must never decrease between periods |
| `fact_patient_stock` | `active_end` | integer or null | 0 or more, null means NR | yes | Stock; never summed across periods |
| `fact_patient_flow` | `new_enrolled` | integer or null | 0 or more, null means NR | yes | Flow; summed across periods |
| `fact_patient_flow` | `ltfu`, `transferred_out`, `stopped`, `died` | integer or null | 0 or more, null means NR | yes | Flow; feed the retention denominator |
| `fact_patient_age` | `age_band` | enum | `u15`, `15_29`, `30plus` | no | Sum must equal `active_end` for the condition |
| `fact_workforce` | `cadre` | enum | `doctors`, `clinical_officers`, `nurses_midwives`, `pharmacy_lab`, `other` | no | One person counted once |
| `fact_supply` | `availability` | enum | `always`, `sometimes`, `never`, `not_applicable`, `not_reported` | no | Ordered scale; never rendered as a number |
| `fact_facility_period` | `months_with_mentorship` | integer | 0 to 3 | yes | Produces both the quarterly and the monthly definition of 3.4 |
| `fact_facility_period` | `quality_score` | integer or null | 0 to 100, null means not assessed | yes | Null is not zero; drives indicator 2.4 numerator only when `critical_met` is yes |
| `fact_facility_period` | `readiness_class` | enum | `green`, `amber`, `red`, `not_assessed` | yes | From the AFRO readiness tool thresholds |
| `fact_quality` | `completeness` | decimal | 0 to 1 | no | Complete returns over facilities expected |
| `fact_quality` | `ltfu_rule_compliant` | boolean | – | no | False excludes retention from the regional aggregate |
| `fact_quality` | `confidence` | enum | `high`, `medium`, `low`, `not_assessed` | no | Per indicator group, declared by the country |
| `gold_indicator` | `numerator`, `denominator` | integer or null | – | yes | Both published; a value without them is not displayed |
| `gold_indicator` | `value` | decimal or null | – | yes | Null where either part is null; never coerced to zero |
| `gold_indicator` | `suppressed` | boolean | – | no | True where the numerator is below five in an external view |
| `gold_indicator` | `as_of` | date | – | no | Closing date of the period, from Section 1 |

## 3. Indicators

The sixteen indicators: numerator, denominator, grain, disaggregation, and
the display rules that apply.

| Code | Indicator | Numerator | Denominator | Grain | Disaggregation | Display rule |
|---|---|---|---|---|---|---|
| 2.2 | Facilities assessed for readiness | Facilities with a readiness class this year | Facilities assessed | facility to country | readiness class | Show the class distribution, never a mean score alone |
| 2.3 | Facilities initiating PEN-Plus services | Facilities with status operational or started_this_period | None; a count | facility to country | region, project_supported | Count, with the number of districts as context |
| 2.4 | Facilities achieving quality standards | Facilities with score 80 or above and critical_met yes | Facilities assessed against the checklist | facility to country | none | Display the assessed denominator; an unassessed country is blank, not zero |
| 2.5 | Patients ever enrolled | Sum of ever_enrolled over the four tracers | None; a count | country | condition | Label as enrolments, not persons, while deduplication is facility level |
| 2.6 | Patients active in care | Sum of active_end over the four tracers | None; a stock | country | condition, age band | Never summed across periods |
| 2.6b | Twelve-month retention | Cohort patients with a visit in the period | Cohort minus deaths, transfers and stopped | country | condition | Excluded from the regional aggregate where `ltfu_rule_compliant` is false |
| 3.2 | Trainers of Trainers trained | Trained this period flagged as ToT | None; a count | country | cadre, sex | Cumulative line plus period bars |
| 3.3 | Health workers trained in the year | Sum of trained across the four quarters | None; a count | country | cadre, sex | Annual figure only; never shown per quarter as an annual value |
| 3.4 | Facilities with active mentorship | Facilities with months_with_mentorship of at least 1 | Operational facilities | facility to country | none | Show the monthly variant alongside for partner reconciliation |
| 5.1 | Reporting completeness | Complete returns received | Facilities expected to report | country | none | Travels with every other figure of the same country and period |
| 1.1 to 1.3 | Policy and planning milestones | Countries with the milestone achieved and a document named | 31 countries | country | milestone | A Yes without a document title is not counted |
| 4.1 | Resource mobilization round table | Countries having held it in the year | 31 countries | country | none | Annual only |
| 5.1 HIS | Integration into the national system | Countries fully or partially integrated | 31 countries | country | integration level | Three-level scale, never collapsed to yes or no |
| 6.1 | Communication products | Products published in the year | None; a count | country | product type | Consent confirmation displayed with the count |

> Ten of these (2.2 through 5.1 reporting completeness) are computed into
> `gold_indicator` in this build. The remaining six are exposed per country
> from `fact_governance` instead — see `docs/architecture.md`, "Indicators
> not aggregated into gold_indicator", for why.

## 4. Display rules

| Rule | What the interface must do | The failure it prevents |
|---|---|---|
| Denominator always visible | Show n and N on the element or on hover for every rate | A 100 per cent built on two patients read as excellence |
| No league table | Distribution and gap to milestone; no ordinal ranking of countries | A ranking that reflects reporting behaviour rather than performance |
| NR is a gap | Break the line; never plot NR as zero; name NR in the legend | A country that did not report appearing to have collapsed |
| Completeness travels | Mute the figure and show the share when completeness is below 80 per cent | A partial national total read as a complete one |
| Suppression | Suppress and flag cells with a numerator below five in external views | Re-identification in a small cohort |
| Cohort separation | Phase 1 and phase 2 countries in separate series for the first year | New countries dragging the regional average and being read as failing |
| Series break | Draw a discontinuity where the condition list or frequency changed | A definitional change read as a fall in the cohort |
| Stock and flow | No control that sums a stock across periods | Active patients added across four quarters |
| Colour plus label | Every status carries a mark or a word, never hue alone | Inaccessible to colour-blind users and to greyscale printing |
| As-of and definition | Every figure states its closing date and the rule applied | Two figures from different definitions compared as if equal |
| No front-end arithmetic | The site formats and filters; it never computes an indicator | A second source of truth that silently diverges from the published formula |
| Hold state is shown | A country on hold appears as awaiting clarification, not as missing | A wrong figure published because a query was pending |

## 5. Bundle

| File | Screen | Contents | Size budget |
|---|---|---|---|
| `manifest.json` | all | Build date, source periods, form version, data model version, per-country hold flags | 5 KB |
| `overview.json` | 1 | Headline figures, milestone strip, country status list | 80 KB |
| `indicators.json` | 2 | `gold_indicator` for all countries and periods, with numerator and denominator | 300 KB |
| `countries/{iso3}.json` | 3 | All indicators, trend, completeness, confidence, facility summary, open queries | 40 KB each |
| `quality.json` | 4 | Completeness and timeliness by country and period, confidence, definition compliance | 60 KB |
| `facilities.json` | 5 | `dim_facility` joined to the latest `fact_facility_period` | 200 KB |
| `strings.{lang}.json` | all | Interface strings and indicator labels in English, French and Portuguese | 30 KB each |

> This build ships the language strings as build-time JSON imports under
> `/i18n` rather than runtime-fetched `strings.{lang}.json` bundle files —
> see `docs/architecture.md`, "Internationalisation."

## 6. Backlog

Build order, with the acceptance test that closes each item.

| Order | Item | Done when |
|---|---|---|
| 1 | Parser reads a completed return into records | A filled form produces a record set with no manual step, and an altered structure is rejected with a clear message |
| 2 | Store and load | Two consecutive returns from one country load, are versioned, and a correction creates a new version without overwriting |
| 3 | Quality control wired to the load | A return with a deliberate error is held, listed in the query register, and absent from gold |
| 4 | Indicator computation | All sixteen indicators compute with numerator and denominator, and a recomputation reproduces a prior figure exactly |
| 5 | Bundle export | Static JSON produced with a manifest, within the size budgets |
| 6 | Screen 1 and screen 3 | Overview and country profile render from the bundle, with completeness visible without interaction |
| 7 | Screen 4 | Data quality screen shows completeness, confidence, open queries and definition compliance |
| 8 | Screen 2 and screen 5 | Indicator detail and facility view |
| 9 | Display rules audit | Every rule of sheet 4 demonstrated on a real return, item by item |
| 10 | Accessibility, print and languages | Keyboard operation, contrast, PDF export, and the three language bundles |

Items 1–5 were substantially in place before this rebuild (see
`docs/architecture.md` for the fixes made to items 3 and 4). Items 6–8 are
implemented in this rebuild's `site/`. Item 9 has not been run as a
systematic audit against a real return, because no real Phase Two return has
been received yet — every return currently in the store is `historical`.
Item 10 is partially done: keyboard operation and the three languages are
implemented; PDF export relies on the browser's native print-to-PDF via the
print stylesheet rather than a generated PDF file.
