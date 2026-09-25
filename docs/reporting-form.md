# PEN-Plus quarterly country report — the real form

> Transcribed from `Phase_2_PEN-Plus_Reporting_Tools.docx` for readability and
> diffability in version control. The original `.docx` is kept alongside this
> file; where the two differ, the `.docx` is authoritative. This is the
> document `pipeline/src/penplus_pipeline/parse.py` is built to read — see
> `docs/architecture.md`, "Indicator list corrected against the real
> reporting forms", for what this corrected relative to `docs/data-model.md`.
>
> **Revision note (2026-09-25).** This transcription was updated against a
> new validated copy of the form (source folder: `Data collection tools/`,
> filename `Phase_2_PEN-Plus_Quaterly_Reporting_Tools.docx`). Unlike the
> previous copy, this one does not declare its own version number, so it is
> referred to here as simply "the current form"; everywhere this document
> says something changed, it means changed relative to the copy this
> transcription previously described. The pipeline has not yet been rebuilt
> against every change listed below — see `docs/architecture.md` for exactly
> what has and has not landed in code.

"The NCD National Professional Officer in each WHO Country Office completes
this form with the national programme and the PEN-Plus sites. The returns
from all countries are aggregated at regional level to follow progress and
to produce the regional reports."

Rules stated on the form itself: one return per country per quarter, for the
quarter named in section 0 and no other; write 0 where there were none — a
blank cell is read as not reported, never as zero; choose from the drop-down
lists rather than typing; every Yes on a policy or plan needs the title of
the document that proves it; do not add, delete or move rows, tables or
sections, because the return is read automatically.

## What changed from the previous copy of this form

- **Three priority conditions, not four.** Every table that used to carry
  type 1 diabetes / sickle cell disease / rheumatic heart disease / **severe
  hypertension** now carries only the first three. Severe hypertension is no
  longer a named tracer condition anywhere in the indicator tables; it
  survives only inside the general "other severe NCDs managed in PEN-Plus
  clinics" catch-all line. This changes the denominator of indicators 2.1,
  2.5 and 2.6. A total computed under the old four-condition definition and
  one computed under the new three-condition definition are not the same
  figure — this is a definition change of exactly the kind CLAUDE.md's rule
  8 has in mind, and it needs its own note wherever 2.5/2.6 totals are
  shown, distinct from the funding-round break.
- **Each indicator now states its own reporting frequency.** Section 7 adds
  an "RF frequency" column — Annual, Semi-annual, or Semi-annual/Annual — for
  every one of the sixteen indicator codes. Previously the form treated
  everything as either "every quarter" or "Q4, or when it changed"; now the
  frequency is indicator-specific and explicit. A country not reporting an
  annual indicator in Q2 is not a completeness problem — it is not due.
- **Section 5.1 is now partly self-reported.** Reporting completeness and
  timeliness used to be calculated only by the Regional Office from the
  facility-return counts in section 0. The current form still asks for
  those counts, but indicator 5.1 now also asks the country to report its
  own completeness (%) and timeliness (%) directly. The two should agree;
  where they do not, that disagreement is itself a data-quality signal.
- **A "Data quality and reconciliation" block is now part of the form**,
  under focus area 5: the country self-attests whether facility counts in
  Annex A reconcile with indicator 2.3, whether patient totals reconcile
  with 2.5/2.6, and whether mentorship totals reconcile with 3.4, plus
  whether anything changed in definitions or a previous figure was
  corrected. This used to be a note ("the Regional Office checks this on
  receipt") rather than a field the country fills in.
- **Facility performance data has moved out of this form.** Annex A here is
  now the facility **register** only (identity: name, region, district,
  level, service start date, status, project-supported, conditions managed).
  The performance side — ever enrolled, active in care, newly enrolled,
  mentorship, quality score, critical criteria, readiness band — moves to a
  new, separate, **monthly** form. See "The new monthly facility return"
  below.
- **The certification block is gone.** No more name/signature/date sign-off
  table for the national programme focal point, the WHO Country Office/NPO,
  and the M&E focal point.
- Smaller wording and structure changes: 2.2's readiness classes are now
  named low/medium/high band rather than Green/Amber/Red with explicit
  percentage cut-offs; 2.4 and 3.4 now show their numerator, denominator and
  percentage as three explicit columns rather than leaving the rate
  implicit; 2.5 moves "newly enrolled this quarter" into the main table
  instead of the optional supplementary block; 4.1 drops the separate
  "PEN-Plus or severe NCD budget line" question and keeps only the round
  table item; section 0 adds "period covered (from–to)" and drops "closing
  date of the quarter" and "is this the country's first return".

## Section 0 — Identification, national context and reporting completeness

Country, reporting quarter, period covered (from–to), year, NPO/WHO Country
Office focal point, national programme focal point, M&E focal point, date
completed.

National context and reporting completeness, one table: health districts in
the country; first-referral/district hospitals in the country; health
districts where PEN-Plus services are offered; PEN-Plus facilities expected
to report this quarter; facilities submitting a complete/partial/no return.

## Section 1 — Governance and leadership (focus area 1)

| Code | Results Framework indicator |
|---|---|
| 1.1 | PEN-Plus integrated into the national NCD strategy and UHC agenda |
| 1.2 | Integrated or stand-alone PEN-Plus Plan developed, approved, launched and under implementation |
| 1.3 | Costed National Operational Plan (NOP) on PEN-Plus developed and launched |

Each row: status, year achieved, document/evidence. "A Yes without a
document title is not counted." Plus a table of the quarter's activities
under this focus area (activity, status, output/evidence).

## Section 2 — Service delivery and disease management (focus area 2)

- **2.1** National guidelines/protocols adapted, validated and disseminated:
  per priority condition (T1D, SCD, RHD, other) — adapted and validated,
  disseminated to all PEN-Plus sites, document title/date.
- **2.2** Secondary-level facilities assessed for readiness: number
  assessed, this quarter vs. year to date; facilities in the low / medium /
  high readiness band.
- **2.3** Facilities initiating and actively providing PEN-Plus services:
  facilities that have initiated PEN-Plus services (cumulative); of these,
  facilities active during the reporting period. "Must match the facilities
  listed in Annex A."
- **2.4** Facilities achieving PEN-Plus quality standards: facilities
  assessed with the quality checklist; facilities scoring ≥80% AND meeting
  all critical criteria (numerator); facilities initiating PEN-Plus services
  per 2.3 (denominator); proportion achieving quality standards (%) —
  numerator, denominator and rate are now all explicit columns.
- **2.5** Unique patients ever enrolled: per priority condition (T1D, SCD,
  RHD) — ever enrolled cumulative, and newly enrolled this quarter, plus a
  TOTAL row across the three conditions.
- **2.6** Patients active in care and 12-month retention: per priority
  condition — active in care at end of quarter, retention numerator,
  retention denominator, retention % — plus TOTAL. A supplementary table
  follows for patient movement this quarter (lost to follow-up, transferred
  out, stopped treatment, died), per condition, plus a line for other severe
  NCDs managed in PEN-Plus clinics.

Plus a table of the quarter's activities under this focus area.

## Section 3 — Capacity building and workforce development (focus area 3)

- **3.1** WHO Academy PEN-Plus course completion: cumulative, by
  female/male/other-or-not-stated, plus total.
- **3.2** Health workers trained as Trainers of Trainers: cumulative, by
  cadre (medical doctors/specialists; clinical officers/associates;
  nurses/midwives; pharmacy/laboratory staff; other cadres), female/male/
  other-or-not-stated, plus total.
- **3.3** Health workers trained in PEN-Plus: this quarter, by the same
  cadre breakdown, plus a year-to-date total column reported directly by the
  country rather than accumulated by the Regional Office from four returns.
- **3.4** Facilities with an active mentorship programme: facilities
  receiving at least one documented mentorship visit this quarter
  (numerator); total facilities providing PEN-Plus services (denominator);
  proportion with active mentorship (%).

Plus a table of the quarter's activities under this focus area.

## Section 4 — Health financing, medicines and service continuity (focus area 4)

- **4.1** Annual resource-mobilization round table (annual): round table
  held to mobilize resources for PEN-Plus or broader NCD services (response,
  evidence/date). The previous "budget line exists" question is gone.
- Quarterly tracer medicines and diagnostics: availability across PEN-Plus
  sites, and facilities with at least one day of stock-out this quarter, for
  insulin; insulin delivery supplies/syringes/needles; blood glucose test
  strips; hydroxyurea; benzathine benzylpenicillin; sickle cell rapid or
  confirmatory tests; HbA1c testing; echocardiography/ultrasound access.

Plus a table of the quarter's activities under this focus area.

## Section 5 — Monitoring, evaluation and data quality (focus area 5)

- **5.1** PEN-Plus indicators integrated in the national HMIS/DHIS2: whether
  indicators are integrated/configured; number of PEN-Plus indicators
  configured; at least one full reporting period received through the
  national system; **reporting completeness for this quarter (%)** and
  **reporting timeliness for this quarter (%)**, both now entered directly
  by the country rather than only calculated from section 0; frequency of
  data collection at first-referral level and, where applicable, primary
  care level.
- **Data quality and reconciliation** (new): facility counts in Annex A
  reconcile with indicator 2.3 — yes/no/explain; patient totals reconcile
  with 2.5 and 2.6 — yes/no/explain; mentorship totals reconcile with 3.4 —
  yes/no/explain; any change in definitions, source systems or
  deduplication method since the last return; any correction to a
  previously reported figure.
- Confidence and means of verification: one row per data domain — facilities
  and coverage; patients; workforce; quality/mentorship; governance/
  financing/HMIS — each with a confidence level (High/Medium/Low), main
  limitation, and whether evidence is held on file.

## Section 6 — Communication and visibility (focus area 6)

**6.1** Communication and visibility products: number this year, by
language and evidence, for press releases/media stories; videos/patient
stories; advocacy briefs/reports; social media campaigns/digital products;
other; plus a TOTAL row.

## Section 7 — Quarterly progress summary

A recap table listing all sixteen indicator codes, now with **the reporting
frequency of each one stated explicitly** (Annual, Semi-annual, or
Semi-annual/Annual), alongside the previous verified value, the current
value or status, and a comment on any change. This table is the form's own
authoritative list of the sixteen indicator codes and, as of this revision,
of their individual reporting cadence.

## Section 8 (narrative, not parsed)

Key achievements, main bottlenecks, corrective actions, support required
from WHO AFRO/partners, and major risks or assumptions that changed —
free-text narrative. None of this feeds an indicator, so `parse.py` does
not read it. The certification/sign-off block that used to follow this
section has been removed from the form.

## Annex A — Facility register

One table now, not two: Facility ID, Facility name, Region/province,
District, Level, Service start date, Status, Project-supported?, Conditions
managed. "Update only when a facility changes." The quarterly performance
columns that used to sit alongside this register (ever enrolled, active in
care, mentorship, quality score, critical criteria, readiness class) have
moved to the new monthly form described next.

## The new monthly facility return

`PEN-Plus_Monthly_Facility_Return.docx` is a new, separate form: one return
per country per month, at facility grain, read automatically like the
quarterly form. Header: country, reporting month, year, facilities expected
to report, returns received, NPO/WHO Country Office focal point, date
completed. One row per PEN-Plus site: Facility ID, Facility name, Return
status, Ever enrolled\*, Active in care\*, Newly enrolled\*, Mentorship
visit this month?, Quality score %, All critical criteria met?, Readiness
band. The footnote: "\*Counted across the three priority conditions: type 1
diabetes, sickle cell disease and rheumatic heart disease. Ever enrolled is
cumulative since the site started PEN-Plus; active in care and newly
enrolled cover this month only. Quality score, critical criteria and
readiness band change only when the site is reassessed, so carry forward the
last assessment where there was none this month."

This is a genuine cadence change — facility performance moves from quarterly
to monthly — not a new concept for the store: `schema.sql`'s `dim_period`
has carried a `rhythm` column (`monthly` / `quarterly` / `annual`) since it
was first written, and `fact_facility_period` already existed with exactly
this column set, its `mentorship_visit` column commented "v3 form: yes/no
per quarter, not a month count" in anticipation of a monthly successor. The
one field this form asks for that the current schema does not yet have a
column for is **newly enrolled, per facility, per month** — everything else
maps onto an existing column.

**Status: documented, not yet wired into the pipeline.** `parse.py` does not
yet read this form, the store is not yet loaded from it, and no screen
consumes facility-level monthly data. Building that is future work, tracked
separately from this revision.

## Phase 1 form (legacy, for historical context only)

`Phase_1_PEN-Plus_Reporting_Tools.docx` is unchanged from the previous
validated copy: the earlier, monthly narrative report NCD National
Professional Officers completed before the Phase Two Results Framework
existed — mostly free-text (activities, achievements, pillar/phase progress
against a four-pillar/five-phase implementation model, partner and Helmsley
Charitable Trust fund tracking) plus two numeric tables — patient enrolment
and health workers trained, both by year and condition since PEN-Plus began
in the country. `seed_history.py` and the ICPPA/monitoring workbooks it
reads are built to approximate this shape, not the quarterly form; its
governance milestones are Phase 1 pillar activities (e.g. "Develop and
disseminate clinical protocols"), not the same three Results Framework
indicators as 1.1–1.3. See `docs/architecture.md` for why the two are kept
distinct rather than merged.
