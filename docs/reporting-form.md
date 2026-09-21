# PEN-Plus quarterly country report — the real form

> Transcribed from `Phase_2_PEN-Plus_Reporting_Tools.docx` (version 3) for
> readability and diffability in version control. The original `.docx` is
> kept alongside this file; where the two differ, the `.docx` is
> authoritative. This is the document `pipeline/src/penplus_pipeline/parse.py`
> actually reads — see `docs/architecture.md`, "Indicator list corrected
> against the real reporting forms", for what this corrected relative to
> `docs/data-model.md`.

"This document carries the same questions, in the same order, as the Excel
quarterly template, version 3. Sections 1 to 6 are the six focus areas of
the Results Framework in its own numbering, each with its indicators and the
country activities carried out under it, so the return maps directly onto
the report to partners."

Rules stated on the form itself: write 0 where there were none — a blank
cell is read as not reported, never as zero; every Yes on a policy or plan
needs the title of the document that proves it; items marked Q4 are
completed with the fourth-quarter return, earlier only if something
changed.

## Section 0 — Identification and reporting completeness (every quarter)

Country, reporting quarter, year, closing date of the quarter, NPO/WHO
Country Office focal point, national programme focal point, M&E focal
point, date completed, whether this is the country's first return on this
template.

National context: health districts in the country; first-referral/district
hospitals in the country; health districts where PEN-Plus services are
offered.

Facility returns this quarter: PEN-Plus facilities expected to report;
facilities submitting a complete / partial / no return; facilities whose
return arrived by the national deadline. Reporting completeness and
timeliness (indicator 5.1) are both calculated by the Regional Office from
these counts.

## Section 1 — Governance and leadership (focus area 1, Q4)

| Code | Results Framework indicator |
|---|---|
| 1.1 | PEN-Plus integrated into the national NCD strategy and UHC agenda |
| 1.2 | Integrated or stand-alone PEN-Plus Plan developed, approved, launched and under implementation |
| 1.3 | Costed National Operational Plan (NOP) on PEN-Plus developed and launched |

Each row: status, year achieved, document/evidence. "A Yes without a
document title is not counted. Under development is a valid answer and is
reported as progress."

## Section 2 — Service delivery and disease management (focus area 2)

- **2.1** National guidelines/protocols adapted, validated and disseminated
  (Q4, or when status changes): per tracer condition (T1D, SCD, RHD, severe
  hypertension, other) — adapted and validated, disseminated to all
  PEN-Plus sites, year, document title.
- **2.2** Secondary-level facilities assessed for readiness, AFRO readiness
  tool (Q4, or when an assessment is done): facilities assessed, this
  quarter vs. year to date; classified Green (≥80%, all critical
  requirements met) / Amber (60–79%) / Red (<60%, or a critical requirement
  failed). "Must match the facilities listed in Annex A" is the form's own
  cross-check note.
- **2.3** Facilities initiating and actively providing PEN-Plus services
  (every quarter): facilities that have initiated PEN-Plus services
  (cumulative); of these, facilities active during the quarter.
- **2.4** Facilities achieving PEN-Plus quality standards (Q4, or when an
  assessment is done): facilities assessed with the PEN-Plus quality
  checklist; facilities scoring ≥80% AND meeting all critical criteria. "The
  proportion is calculated over facilities assessed, so that a facility not
  yet assessed is not counted as failing."
- **2.5** Unique patients ever enrolled, four tracer conditions (every
  quarter): ever enrolled, cumulative, per tracer + total. Plus: how the
  count was deduplicated.
- **2.6** Patients active in care, and twelve-month retention (active: every
  quarter; retention: Q4): active in care at end of quarter, retention
  numerator (Q4), retention denominator (Q4), per tracer + total. Plus:
  which loss-to-follow-up rule was applied to the retention figures — "only
  retention built on the regional 90-day rule enters the regional
  aggregate." An **optional** block follows for countries whose system
  produces it: newly enrolled, LTFU, transferred out, died, stopped
  treatment, per tracer plus "other severe NCDs" — "not required... a blank
  here is read as not collected and is never counted against the country."

## Section 3 — Capacity building and workforce development (focus area 3)

- **3.1** People completing a PEN-Plus WHO Academy course (pre-filled by WHO
  AFRO from the Academy system, correct only if known wrong): cumulative,
  by female/male/not-stated.
- **3.2** Health workers trained as Trainers of Trainers (every quarter):
  cumulative, female/male/not-stated, by cadre (medical doctors/specialists;
  clinical officers/associates; nurses/midwives; pharmacy/laboratory staff;
  other cadres) + total.
- **3.3** Health workers trained in PEN-Plus (every quarter): this quarter
  only, same cadre breakdown + total — "the annual total is built by the
  Regional Office from the four returns."
- **3.4** Facilities with an active clinical mentorship programme (every
  quarter): facilities receiving at least one documented mentorship visit
  this quarter; facilities providing PEN-Plus services ("should equal 2.3,
  active").

## Section 4 — Health financing, medicines and service continuity (focus area 4)

- **4.1** Annual resource-mobilization round table (Q4, or when held): round
  table held to mobilize resources for PEN-Plus or broader NCD services
  (response, date, document); a PEN-Plus or severe NCD line exists in the
  government budget.
- Tracer medicines and diagnostics (every quarter): availability across
  PEN-Plus sites, and facilities with at least one day of stock-out this
  quarter, for insulin; insulin syringes/pens/needles; blood glucose test
  strips; hydroxyurea; benzathine benzylpenicillin; sickle cell rapid or
  confirmatory tests; HbA1c testing; echocardiography or ultrasound access.

## Section 5 — Health information, monitoring and data quality (focus area 5)

- **5.1** PEN-Plus indicators integrated into the national HMIS/DHIS2
  (integration: Q4): extent of integration (not / partially / fully
  integrated — "a three-level scale, never collapsed to yes or no"); number
  of PEN-Plus indicators configured; at least one full reporting period
  received through the national system; frequency of data collection at
  first-referral level and, where applicable, primary care level.
- Change since the last return: change in definitions/source
  systems/deduplication method; correction to a previously reported figure.
- Confidence declarations, one row per data domain — facilities and
  coverage; patients; workforce; **quality and mentorship**; governance,
  financing, HMIS — each with a confidence level, main limitation, and
  whether evidence is held on file. The Regional Office's own receipt checks:
  Annex A matches 2.3; the mentorship denominator matches 2.3; patients ever
  enrolled are at least as many as those active; facility returns add up.

## Section 6 — Communication and visibility (focus area 6, Q4)

**6.1** Communication and visibility products: number this year, by
language and evidence, for press releases/media stories; videos/patient
stories; advocacy briefs/reports; social media campaigns/digital products;
other; plus a TOTAL row. Safeguard: documented informed consent held for
every product featuring a patient (and parent or guardian consent for
minors).

## Section 7 — Quarterly progress summary

A recap table listing all sixteen indicator codes (1.1, 1.2, 1.3, 2.1, 2.2,
2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 4.1, 5.1, 6.1) with the previous
verified value pre-filled and a comment field for the country to explain any
change — "the current value of each indicator is taken by the Regional
Office from sections 1 to 6; it is not typed again here." This table is the
form's own authoritative list of the sixteen indicator codes.

## Sections 8 and certification (narrative, not parsed)

Key achievements, main bottlenecks, corrective actions, support required
from WHO AFRO/partners, and major risks or assumptions that changed —
free-text narrative, plus a certification block (name/signature/date for the
national programme focal point, WHO Country Office/NPO, and M&E focal
point). None of this feeds an indicator, so `parse.py` does not read it.

## Annex A — Facility register and quarterly facility return (every quarter)

Two tables, introduced by plain paragraphs ("Facility register", "Facility
return this quarter"), not a numbered sub-heading.

**Facility register** (identity, slowly changing, pre-filled after the
first return): Facility ID, Facility name, **Region/province, District**
(in that order), Level, Service start date, Status, Project-supported?,
Conditions managed.

**Facility return this quarter** (performance): Facility ID, Facility name,
Return status, Ever enrolled (four tracers), Active in care (four tracers),
**Mentorship visit this quarter? (yes/no)**, Quality score %, All critical
criteria met?, Readiness class.

## Phase 1 form (legacy, for historical context only)

`Phase_1_PEN-Plus_Reporting_Tools.docx` is the earlier, monthly narrative
report NCD National Professional Officers completed before the Phase Two
Results Framework existed: mostly free-text (activities, achievements,
pillar/phase progress against a four-pillar/five-phase implementation
model, partner and Helmsley Charitable Trust fund tracking) plus two
numeric tables — patient enrolment and health workers trained, both by year
and condition since PEN-Plus began in the country. `seed_history.py` and the
ICPPA/monitoring workbooks it reads are built to approximate this shape, not
the v3 form; its governance milestones are Phase 1 pillar activities (e.g.
"Develop and disseminate clinical protocols"), not the same three Results
Framework indicators as v3's 1.1–1.3. See `docs/architecture.md` for why the
two are kept distinct rather than merged.
