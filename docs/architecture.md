# Architecture notes

This file records decisions that extend or adapt the specification
(`docs/specification.md`) and data model (`docs/data-model.md`), and states
plainly where the build is incomplete rather than filling the gap with
invented data. Where this file and the specification disagree, the
specification wins (per `CLAUDE.md`).

## Stack

| Layer | Choice | Why |
|---|---|---|
| Pipeline | Python, unchanged from the original build | Already written and tested against the form; the specification names it directly. |
| Site | TypeScript, compiled and bundled by Vite, charts via Observable Plot | The specification requires "vanilla JavaScript or a light framework... no build server required in production." A `vite build` produces plain static HTML/CSS/JS with no server process — the build step happens once, ahead of deployment, same as any other static-site toolchain (Jekyll, Hugo). TypeScript and Observable Plot (an SVG-based charting library, no framework runtime) satisfy "expert engineering, latest tooling" without pulling in a UI framework or an SSR server, which the specification explicitly rules out. |

## The pipeline changes made in this rebuild

The pipeline as delivered computed indicators and exported a bundle, but three
things in it did not match the specification's own acceptance criteria:

1. **No validation stage was wired in.** `verdict` was hard-coded to
   `'accepted'` on every load, and `query_register` was never populated —
   directly contradicting acceptance criterion 2 ("A return with a deliberate
   arithmetic error is held, appears in the query register, and does not
   change any published figure"). Added `pipeline/src/penplus_pipeline/validate.py`,
   run between `parse` and `load` in `run.py`, implementing the checks the
   data model already specifies: the patient cascade (active ≤ ever
   enrolled), the age-band reconciliation ("sum must equal active_end for the
   condition," 2_Fields), the longitudinal rule ("must never decrease between
   periods," 2_Fields), and completeness/retention arithmetic. A High-severity
   finding sets `verdict='hold'`, which `transform.py` already excluded from
   `gold_indicator` — that exclusion existed before this change and was
   simply never reachable.
2. **`dim_indicator` had no milestone column**, despite `1_Tables` stating it
   "holds the definition, formula, direction **and milestone**." Added the
   column (migrated in place via `load.py::_migrate`, so the existing store
   is not rebuilt from scratch) and a `regional_value` / `gap` computation in
   `export.py`. See "Milestones" below for why every value is currently
   `null`.
3. **Hard-coded `/mnt/user-data/uploads` paths** in `run.py` for the two
   historical seed workbooks (a path specific to the environment the pipeline
   was first built in). Changed to `<repo>/data/raw/`, which is git-ignored:
   those two files are Regional M&E evidence, not code, and are not part of
   this repository (see "Data included in this repository" below).

`pipeline/src/penplus_pipeline/qc.py` is a separate, older script that
targets a previous version of the reporting form (different section
numbering to `parse.py`). It is not wired into the pipeline and was left
untouched; a future form revision that supersedes v3.0 would need a rewrite
of `validate.py` in the same way, not a resurrection of `qc.py`.

## Indicator list corrected against the real reporting forms

The first pass of this build (including the section above, when it still
said the twelve-per-quarter form's numbering came from the data model
workbook) trusted `PEN-Plus_Dashboard_Data_Model.xlsx`'s `3_Indicators`
sheet for the indicator list and `parse.py`'s section numbering. Once the
real `docs/Phase_2_PEN-Plus_Reporting_Tools.docx` (v3) and
`docs/Phase_1_PEN-Plus_Reporting_Tools.docx` became available, it turned out
neither the workbook's indicator list nor `parse.py`'s section map matched
the actual form. Per `CLAUDE.md`, "the form is the contract" outranks the
data model workbook, so this build now follows the real form and documents
every place the two disagree, rather than silently picking one.

**The real sixteen indicators** (from section 7's own progress-summary
table, which lists the definitive codes) are 1.1, 1.2, 1.3, 2.1, 2.2, 2.3,
2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 4.1, 5.1, 6.1 — not the ten-code list
(missing 2.1 and 3.1 entirely, and coding retention as a standalone "2.6b")
the data model workbook shipped with. `common.py::INDICATORS` now carries
all sixteen, plus `2.6b` kept as a named sub-facet of 2.6 (a genuinely
distinct rate needing its own numerator and denominator, reported alongside
2.6 rather than as a seventeenth headline indicator).

**The real form's section numbers are 0 (identification), 1 (governance), 2
(service delivery), 3 (workforce), 4 (financing), 5 (health information), 6
(communication), Annex A (facilities)** — not the 1/2/3/4/5/6/7 scheme
`parse.py` was first written against, which put identification at section 1
and governance at section 6. `parse.py` is rewritten section-by-section
against the real document; see its module docstring and inline comments for
the exact table-index mapping. Two structural quirks the rewrite had to
handle, because they will bite any future revision to this parser too:

- A **top-level** section banner is a one-row, two-cell table ("1.
  Governance and leadership | Focus area 1. Q4"); a **sub-indicator** banner
  is a one-row, three-cell table with the bare code in its own cell ("2.1 |
  National guidelines... | Q4..."). The two need different detection, and a
  bare code like "2.1" satisfies the top-level regex too, by backtracking
  onto its own decimal point — the sub-indicator check has to run first, or
  every sub-indicator banner truncates to its parent section (2.1 read as
  section 2). This was a real bug caught by
  `pipeline/tests/test_integration_v3_form.py` during this rewrite, not a
  hypothetical.
- An **activity-log or optional-block banner** has the same three-cell shape
  as a sub-indicator banner but a **blank** first cell ("| Activities this
  quarter... | Every quarter"). It carries no key of its own and is not
  data, so `index_tables()` drops it outright rather than let it occupy a
  table-index slot under the still-current key — otherwise every table
  after the first activity log in a section would be off by one.

**Fields that moved, split, or turned out not to exist as assumed:**

- 2.5 (ever enrolled, cumulative) and 2.6 (active in care and retention) are
  **separate tables** in the real form; the original schema and parser
  expected one combined stock table.
- Annex A's facility register lists **region before district** (columns 2
  and 3) and **status before conditions** (columns 6 and 8) — the reverse of
  what the original parser assumed. Getting this backwards silently
  mislabels every facility's geography rather than raising an error, which
  is exactly the kind of mistake `docs/architecture.md` exists to catch
  before it reaches production.
- Annex A's facility return asks a **quarterly yes/no** ("Mentorship visit
  this quarter?"), not the 0–3 month count `fact_facility_period.months_with_mentorship`
  was built for. The column is renamed `mentorship_visit` (migrated via
  `load.py::_migrate`, `CHECK (mentorship_visit IN (0,1))`), and indicator
  3.4's "monthly definition" disaggregation — which depended on the 0–3
  scale existing — is removed rather than kept as dead code.
- The cadre labels in `parse.py::CADRE_KEY` used "and"/"or" wording
  ("medical doctors and specialists"); the real form uses a slash ("Medical
  doctors / specialists"). The mismatch would have silently dropped every
  workforce row rather than raising, since a failed dictionary lookup just
  produces `None` and the row is skipped — no error, no data. Fixed to match
  the real labels exactly.
- The fifth confidence domain is "Quality and mentorship," not "supply" —
  `fact_quality.conf_supply` is renamed `conf_quality`. A `returns_on_time`
  field was added: the form asks for it as part of section 0's completeness
  table, and "reporting completeness **and timeliness**" is explicitly what
  indicator 5.1 measures, but timeliness had no column at all before.
- Indicator 3.2 (Trainers of Trainers, cumulative by cadre) and 3.3 (health
  workers trained this quarter, by cadre) are **two different tables** in
  the real form, not one table read two ways. 3.2 now has its own table,
  `fact_workforce_tot`, additive alongside the existing `fact_workforce`
  (used for 3.3) rather than overloading one table with a `kind` flag, which
  would have forced a primary-key change and a destructive migration for no
  benefit — nothing depended on the old shape yet. Both tables also gained a
  `trained_ns` ("not stated") column: the form offers three sex categories,
  not two.

**Now computable, previously not:** 1.1, 1.2 and 1.3 have **fixed codes** in
the real form's governance table (a `Code` column reading literally "1.1",
"1.2", "1.3"), not a free-text milestone label needing a slug — so
`transform.py` now aggregates them into `gold_indicator` directly ("a Yes
without a document title is not counted" enforced the same way the country
profile already enforced it). Indicator 2.1 (guideline dissemination), 3.1
(WHO Academy completions), 4.1 (resource-mobilization round table), and 6.1
(communication products) are similarly now computed, each from a form field
that has a direct, unambiguous mapping to a count. See "Indicators not
aggregated into gold_indicator" below for what is deliberately still not
computed, and why.

One thing the real form confirmed rather than changed: the historical
governance milestones seeded from `PEN_PLUS_MONITORING.xlsx` (Phase 1 pillar
activities such as "Develop and disseminate clinical protocols") are **not**
the same three Results Framework indicators 1.1–1.3, and are not relabelled
to look like them. They stay under their own free-text slugs in
`fact_governance` — legitimate historical context on the country profile,
but not a stand-in for the real indicator, which has no historical data and
correctly shows as not reported until a real Phase Two return arrives.

`pipeline/src/penplus_pipeline/qc.py` targets a still-earlier form revision
(different section numbering to the v3 form used here) and remains
disconnected from the pipeline, unchanged.

**A table with no source in the real form:** `fact_patient_age` (age-band
disaggregation of 2.6, `u15`/`15_29`/`30plus`) has no corresponding table
anywhere in the v3 form — the age breakdown the data model workbook
describes was apparently dropped from the approved form. The schema and
`transform.py`'s age-band disaggregation of 2.6 are left in place (harmless,
and cheap to revive if a future form revision restores the table) but
`parse.py` no longer populates it, so it will read `null` for every real
return until then.

## Current form revision (2026-09-25)

The country reporting tools were revalidated against a new copy (source
folder `Data collection tools/`, alongside a brand-new
`PEN-Plus_Monthly_Facility_Return.docx`). Full field-by-field detail is in
`docs/reporting-form.md`, "What changed from the previous copy of this
form"; this section is the pipeline-side record of what that meant for code.

- **Three priority conditions, not four.** `common.py::TRACERS` still lists
  `severe_htn` as a fourth entry — deliberately: it is the historical
  condition vocabulary, kept so a previously-loaded return that reported
  severe hypertension still sums correctly (`for c in TRACERS if c in
  stock`, so a return that only ever reported three simply has no fourth
  entry to sum). Nothing was reprocessed or reclassified; a total computed
  under the four-condition definition and one computed under the
  three-condition definition are genuinely different figures, per rule 8
  (a series break belongs wherever the condition list changed), not a bug
  to reconcile away.
- **Indicator 2.1's denominator was a latent bug, now fixed.**
  `transform.py` used to divide by `len(TRACERS)` — a hard-coded four —
  rather than by how many conditions the return actually answered. That
  happened to be correct only by coincidence, while every return asked
  about exactly four conditions. Now divides by `len(reported)`, correct
  for a three-condition return, a four-condition return, or whatever a
  future revision asks about next.
- **`dim_indicator.reporting_frequency`** (new column): the current form's
  section 7 states each indicator's own cadence (annual, semi-annual, or
  semi-annual/annual for 2.6) rather than treating every indicator as
  either quarterly or "Q4, or when it changed". Populated as static
  reference data in `common.py::INDICATORS`, not parsed per return — it is
  a property of the indicator, not something that should vary by country.
  Not yet surfaced on any screen; a screen showing a "not reported this
  quarter" annual indicator should say "not due" instead once it is.
- **5.1 is now partly self-reported.** `fact_quality` gained
  `reported_completeness_pct` and `reported_timeliness_pct` (from the
  country's own answer under 5.1) alongside the existing `completeness`
  (computed by this pipeline from section 0's counts). `export.py` computes
  `completeness_divergence` (the absolute gap between the two, in
  percentage points) once, server-side, so a screen can flag a
  self-reported figure that disagrees with the computed one without ever
  subtracting two numbers itself.
- **A data-quality reconciliation self-attestation block is new**
  (`fact_quality.recon_*`, five columns): the country now answers directly
  whether its own Annex A, patient and mentorship totals reconcile across
  sections, and whether anything changed since the last return. Previously
  this was only ever a note the Regional Office checked on receipt.
- **Annex A lost its performance columns.** See "Indicators not aggregated
  into `gold_indicator`" above.
- **Smaller field changes**, each with its own comment at the call site in
  `parse.py`: section 0 merged national-context and facility-return-count
  into one table and dropped "closing date of the quarter" (now derived
  from the period itself, see `parse.py::_quarter_end_date`) and "is this
  your first return"; 4.1 dropped the "PEN-Plus or severe NCD budget line"
  question; 3.3's fourth column is now a redundant this-quarter total
  rather than a not-stated count, and a fifth column gives a
  country-reported year-to-date total instead of that figure being
  accumulated by the Regional Office from four quarterly returns; the
  "which loss-to-follow-up rule was applied" question is gone from the form
  entirely, so `ltfu_compliant` defaults to `1` for every return parsed
  from the current form (the regional rule is now a fixed definition, not a
  per-quarter self-attestation) rather than gating on a question that no
  longer exists.
- **The new monthly facility return is documented, not wired.** See
  `docs/reporting-form.md`, "The new monthly facility return", for the
  field-by-field mapping onto the existing schema (`dim_period.rhythm`
  already supports `'monthly'`, and `fact_facility_period` already existed
  for exactly this shape) and what remains to build: a parser, load-time
  wiring, and a decision on how the Facilities and Data Quality screens
  should present a monthly-cadence source alongside a quarterly one.

## Milestones

Every indicator can carry a `milestone` (the regional target it is measured
against) and the bundle computes `gap = milestone - regional_value`
end‑to‑end. No milestone value is populated in this build: those numbers live
in the programme's traceability workbook, which is not among the source
documents this rebuild had access to. Rather than invent a plausible-looking
target, `dim_indicator.milestone` is `null` for every indicator, and the site
renders "milestone not yet published" wherever a target is missing (screen 1's
milestone strip, screen 2's gap-to-milestone panel) instead of drawing a bar
against nothing. When the Regional Office supplies the values, they go into
`common.py::INDICATORS` (or a future admin-entry path) and every screen that
reads `dim.milestone` starts rendering the real gap with no other change.

## Indicators not aggregated into `gold_indicator`

All sixteen real indicators (plus the 2.6b retention sub-facet) now have a
`transform.py` computation and appear in `gold_indicator`, so screen 2
("one indicator, all countries") and the country profile's full indicator
table work uniformly across all of them — no special-casing needed in the
front end. Two things are still deliberately left uncomputed, both
documented in code where they'd otherwise look like an oversight:

- **Country-reported aggregates for 2.2, 2.3, 2.4 and 3.4** (the "this
  quarter / year to date" or "facilities assessed" summary tables the form
  asks the country to fill in directly) are not parsed. These four
  indicators were instead computed bottom-up from Annex A's facility-level
  detail, which was auditable against the facility register and was not
  always reconcilable line-for-line with the country's own top-level count
  (the form's own guidance only promised that 2.3 "must match the
  facilities listed in Annex A", not the other three). **As of the current
  form revision (see below), Annex A no longer carries that facility-level
  detail at all** — it moved to a new, separate monthly facility return,
  not yet wired into this pipeline. 2.3 still resolves from the facility
  register's own status column (a fallback that already existed); 2.2, 2.4
  and 3.4 currently have no source to compute from and correctly render as
  not-yet-reported rather than switching over to the country's own aggregate
  answer, which this pipeline has never treated as the primary source.
  Reconciling the two, once the monthly form is wired, is still a reasonable
  follow-up validate.py rule.
- **5.1's HMIS integration extent** (`fact_context.his_integration_level`,
  encoded 0/1/2 for not/partially/fully integrated, since `fact_context`
  only stores integers) is parsed and stored but not folded into the 5.1
  rate that `gold_indicator` publishes, which stays reporting completeness
  only. The data model's own note that this is "a three-level scale, never
  collapsed to yes or no" argues against folding it into a single number at
  all; showing it as its own descriptive field (not yet wired into a screen)
  is the more honest next step than picking a collapse rule unilaterally.

## The "map" on screen 1

The specification asks for "a map of countries by phase and status" that
"situates, it does not rank" and "carries no colour scale that implies
performance." This build renders a grid of country tiles (grouped alphabetically,
coloured by cohort) rather than a geographic choropleth, because no licensed
AFRO boundary file (GeoJSON/TopoJSON) was available among the source
materials, and fetching an unverified one from the internet for a WHO
regional map risked incorrect or disputed boundaries — a worse failure than
an honest non-geographic placeholder. The grid satisfies the same display
rule (situates by phase and reporting status, never ranks) and is not the
first element of the screen. Swapping in a real map means adding a licensed
AFRO boundary file and replacing `renderOverview`'s grid block in
`site/src/screens/overview.ts` — the data feeding it (`overview.json.countries`)
does not change.

## Visual design

The first pass at the site (typography, shadows, header) was flat and
under-designed relative to the sibling NCD Population-based Surveillance
Intelligence Platform that CLAUDE.md names as the design-language reference.
It was revised to match that platform's level of polish -- an editorial
serif (system stack, no font fetch) for headline figures, layered shadows,
a gradient navy header and footer with a dot-grid texture, hover elevation
on interactive cards, and a sticky animated tab bar -- while keeping PEN-Plus's
own stricter palette rule ("one primary colour... one accent... colour is
never decorative"): unlike the NCD platform's multi-hue signal/status
palette, every gradient here is tonal (navy-on-navy), and the accent colour
is still used only for gap-to-milestone and alerts.

Two logos were added to match the specification document's own header
("In partnership with") and the institutional identity a WHO AFRO dashboard
is expected to carry: the WHO AFRO mark in the header, and the Helmsley
Charitable Trust mark in the footer's partnership credit. Both come from
files supplied alongside the specification documents, not fetched from the
internet.

Two correctness bugs surfaced during this pass and are fixed, not just
styled over:
- Observable Plot renders a degenerate, oversized frame when every value in
  a series is `null` (an all-NaN y-domain) -- a country/indicator combination
  with no reported data at all produced a chart that was mostly blank
  whitespace instead of a compact message. `src/charts/empty.ts` is now
  checked by every chart function before calling `Plot.plot`, and renders the
  same honest "no published figure" state the rest of the site uses instead.
- Several table column headers and filter options (facility status, project-
  supported, readiness class, severity, "Yes"/"No") were hard-coded in
  English regardless of the selected language. They now route through the
  same i18n registry as everything else (`src/lib/vocab.ts` builds the key
  for each controlled vocabulary). Country and facility *names* remain in
  English, since translating 31 country names and hundreds of facility
  names is a data-translation exercise, not a UI-copy one.

## Demo mode

Most of the real bundle is honestly `NR` -- no real Phase Two return has
been submitted yet -- which is correct behaviour but makes it hard to judge
layout, density and chart legibility against realistic volumes. Rather than
soften "no mock data in site/data" (a working preference for good reason:
CLAUDE.md notes mock data "has a habit of reaching production and being read
as real"), demo mode is a parallel, unmistakable path:
`pipeline/tools/generate_demo_bundle.py` generates a fully invented but
internally consistent bundle by running synthetic records through the exact
same `load_return` / `transform.build` / `export.export` the real pipeline
uses (so it obeys the same suppression, null-discipline and stock/flow
rules, not numbers that could never legitimately occur), and writes it to
`site/public/demo-data` -- a different directory from `site/public/data`,
never merged with it. The site only loads it when a viewer explicitly turns
on demo mode (`?demo=1`, or the header toggle), which persists per-browser
via `localStorage` and shows a permanent accent-coloured banner on every
screen for as long as it's on (`src/lib/demo.ts`, `src/lib/bundle.ts`). No
demo figure is ever written into `site/public/data` or the real store.

## Visual design, round two

The first design pass (a flat header, plain white hero cards) still read as
under-designed once judged against realistic data volumes, and a second,
more ambitious pass followed: a full-width dark hero band on screen 1 with
icon-led "signal cards" for the four headline figures (`src/components/
icons.ts` -- small inline SVGs, no icon-font CDN) and a one-sentence
narrative summary underneath, both patterned directly on the NCD platform's
`.hero`/`.hero-right`/`.exec-message` treatment. The `.hero-strip`/
`.figure-card` classes from the first pass are removed rather than left
dead once the hero band replaced their only caller.

## Regional aggregates are computed once, server-side

`export.py::regional_value()` is the only place a per-country gold figure is
summed into a regional total (for the four hero figures, the milestone
strip, and each indicator's gap-to-milestone panel). The site never sums a
series itself — every place a total might look derived (screen 2's
gap-to-milestone row, for instance) reads a field the bundle already
computed. This was very nearly violated once during this build (a client-side
`reduce()` was written for the gap-to-milestone panel and then removed
in favour of `dim.regional_value` from the bundle) — noted here as the kind
of front-end arithmetic rule 1 is written to catch.

## Internationalisation

Interface strings are hand-maintained JSON files in `/i18n` (English source
plus French and Portuguese translations), bundled at build time via Vite's
JSON import rather than fetched at runtime as `5_Bundle` describes. The
string set is small and fixed, so this avoids an extra HTTP round trip
without losing the point of keeping copy out of components: a translator
still only ever edits `i18n/strings.{lang}.json`, never a `.ts` file.

## Data included in this repository

`pipeline/src/penplus_pipeline/penplus.db` and the exported bundle in
`site/public/data` are committed as the build's known-good state — 41
historical returns across 20 countries, seeded from the ICPPA 2026 extraction
and the Phase 1 monitoring workbook (both tagged `source_kind='historical'`
and excluded from `gold_indicator` where they'd misrepresent Phase Two
data). The two raw seed workbooks themselves are **not** included
(`data/raw/` is git-ignored): they are Regional M&E source evidence, not
derived output, and are out of scope for a code repository regardless of
its visibility.

Whether the derived facility-level data belongs in a *public* repository is
a separate question the specification itself flags: "Facility-level figures
are visible in the internal view only. The public view aggregates to
district or country and applies suppression" (Security and data protection).
This build does not yet implement that distinction — there is one bundle,
not an internal and a public variant — so publishing this repository
publicly as-is would expose facility-level detail the specification reserves
for the internal view. See the repository's top-level README for the
recommendation made about this before publishing.
