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

Ten of the sixteen indicators (2.2 through 5.1 reporting completeness) are
computed by `transform.py` into `gold_indicator`. The remaining six —
1.1–1.3 (policy milestones), 4.1 (resource mobilization round table), 5.1 HIS
(system integration level), 6.1 (communication products) — are governance
and milestone facts sourced from free-text rows in Section 6 of the form
(`fact_governance`), where the row label itself (not a fixed code) is what
the form contains. Mapping those six specific labels to fixed indicator
codes requires the actual form template or the traceability workbook, which
this rebuild did not have; guessing the mapping risked silently miscounting
a milestone. They are exposed honestly instead, per country, in
`countries/{iso3}.json.governance` and rendered on the country profile
(screen 3) with the "a Yes without a document title is not counted" rule
enforced in the UI (`src/lib/status.ts::statusFromGovernance`). Screen 2
("one indicator, all countries") is scoped to the ten indicators that have a
comparable cross-country numeric value; extending it to the six governance
indicators is a follow-up once the label-to-code mapping is confirmed.

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
