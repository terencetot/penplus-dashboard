# PEN-Plus dashboard: refinement pack (version 2)

Copy this folder into the `penplus-dashboard` repository as `docs/refinement/`, copy the two workbooks of
`02_data/` into `data/raw/` (git-ignored), then give Claude Code the prompt below. It works in six stages and stops
after each one.

## Contents
| Path | What it is |
|---|---|
| `01_AUDIT_REPORT.md` | Root causes of every wrong figure, phase fit, screen-by-screen plan. Read first. |
| `02_data/PEN-Plus_country_data_ICPPA2026_v2.xlsx` | The team's extraction, kept intact, plus (in yellow) Kenya, Malawi, Nigeria from the two decks v1 lacked, a "Value type" column, new data-quality flags, and the machine-readable sheet `Load_Map_Other_Figures`. |
| `02_data/PEN_PLUS_MONITORING.xlsx` | The phase-1 monitoring workbook (phases, pillars, districts, profiles, finance). |
| `02_data/implementation_phase_reconciliation.csv` | 14 steps per country from the workbook, the official ICPPA phase map, the phase to publish. |
| `02_data/facility_register.csv` | 43 facilities / pilot sites, ready for geocoding. |
| `02_data/data_queries.csv` | 28 queries to seed the query register (7 High). |
| `02_data/GEOCODING_PROTOCOL.md` | How to get coordinates without guessing. |
| `03_reporting_form/` | The new national quarterly tool and its diff against the v3 form the pipeline parses. |
| `04_data_quality/` | Rebuild spec for the Data quality screen; South Sudan data-system assessment. |
| `05_design/` | PEN-Plus design brief, token additions, country map / coat-of-arms spec. |
| `06_evidence_slides/` | 40 slide images, one per figure that matters, named by deck and page. |

## The prompt for Claude Code

```
Read CLAUDE.md, then docs/refinement/00_START_HERE.md and docs/refinement/01_AUDIT_REPORT.md in full.
This is the PEN-Plus dashboard: ICPPA 2026 is only the source of the baseline country data, never the branding.
CLAUDE.md's rules still apply; if anything in the pack conflicts with them, stop and tell me.
Work on a new branch `refinement-v2`. Do the stages in order. After each stage STOP with a short summary,
test results and screenshots, and wait for my "go".

Stage 1 - Fix the readers (no new data yet)
- seed_history.from_monitoring_phases: the country is in column index 2, not 3. Add the aliases
  "Democratic Republic of Congo", "Congo, Republic of", "KEN Kenya" to common.COUNTRIES. Test: 20 countries read.
- Take severe_htn out of every sentinel total (common.TRACERS); it stays visible under other conditions.
- Stop building facilities by splitting the "Site or district names" text.
- Add regression tests for each of these three bugs.

Stage 2 - Reporting tool and indicators
- Align parse.py, validate.py, common.py and the indicator list with docs/refinement/03_reporting_form/ (new tool):
  2.5 = all PEN-Plus patients ever enrolled; 2.6 = sentinel T1D/SCD/RHD cohort (ever, new, active);
  HMIS integration = 5.2. Keep reading v3 returns for history.
- Never read a country-entered retention %; compute the approximate retention defined in
  04_data_quality/DATA_QUALITY_SPEC.md section 3. Add a fixture return for the new tool.

Stage 3 - Baseline data
- Use data/raw/PEN-Plus_country_data_ICPPA2026_v2.xlsx. Honour "Include in country total" and "Value type"
  (flow = running sum; cumulative = a stock, never summed - only its latest row is Y; active = 2.6 active;
  point-in-time = dated count; unclear = do not load). Keep source document + slide on every value as provenance.
- Load the sheet Load_Map_Other_Figures (rows with Load? = Y) into the indicators it names.
- Build 3.3 health workers trained from Staff_Trained_by_Year and the load map.
- Load facilities from 02_data/facility_register.csv and phases from implementation_phase_reconciliation.csv
  (publish phase_to_publish; show the workbook steps; flag disagreements).
- Seed the query register from 02_data/data_queries.csv; an open High query holds the figure it concerns.
- Print a reconciliation table, old value vs new value and why. Expected: UGA 2,241 -> 2,226;
  BFA 3,902 -> SCD 500; COD 570 -> SCD 7; ZWE 4,590 held; SLE 1,829 and LBR 90 unchanged; KEN 559 (T1D 310);
  TZA 558 active; ETH 865, MOZ 254, ZMB 1,397 (SCD 712, T1D 93) newly present; phases 1 / 15 / 3 / 1 + 11 no return.

Stage 4 - Facilities and map
- Ask me whether facility names may be published; implement as a configuration flag.
- scripts/geocode_facilities.py exactly per 02_data/GEOCODING_PROTOCOL.md; show me data/geocode_review.csv;
  never set geo_checked yourself.
- Facility point map on the Facilities screen after the KPI row: status by shape and label, WHO disclaimer,
  only geo_checked points, the rest listed as "location to confirm".

Stage 5 - Screens
- Every fix in 01_AUDIT_REPORT.md section 4. Data quality screen rebuilt exactly to
  04_data_quality/DATA_QUALITY_SPEC.md (rules R01-R17 in validate.py, all 31 countries, no respondent names or e-mails).
- Banner on every screen while no second-round return exists: "Baseline from country presentations at
  ICPPA 2026 (June 2026), not yet validated quarterly returns."

Stage 6 - Design
- Keep the existing PEN-Plus tokens; add 05_design/tokens.penplus.additions.css; follow 05_design/DESIGN_BRIEF.md.
- Country profile header with country map and coat of arms from site/public/assets/countries/<ISO3>/
  (05_design/COUNTRY_ASSETS.md), behind the SHOW_COAT_OF_ARMS flag, with graceful fallbacks.
- Screenshot every screen at 1440 px and 390 px.

At the end: make test green, rebuild the bundle, list every published figure that changed with its source
slide, and do not merge or push until I approve.
```

## Decisions only the team can take
1. Publish facility names (stage 4).
2. Coats of arms on a public WHO page (check with AFRO communications).
3. The regional headline WHO AFRO stands behind (Q-REG-01).
4. Answers to the 7 High queries, and the 5 phase disagreements (Q-PHS-01).
5. The retention formula and a GPS / DHIS2 UID column in Annex A, before the LimeSurvey version goes out.
