# PEN-Plus regional dashboard

Regional monitoring dashboard for the WHO AFRO PEN-Plus programme, Phase Two.
Built from the quarterly country reporting form. Static site, no backend.

Read `docs/PEN-Plus_Dashboard_Specification.docx` (transcribed for diffing at
`docs/specification.md`), `docs/PEN-Plus_Dashboard_Data_Model.xlsx`
(transcribed at `docs/data-model.md`), and `docs/Phase_2_PEN-Plus_Reporting_Tools.docx`
(the actual v3 quarterly form `parse.py` reads) before touching the pipeline.
They are the contract, and where they disagree with each other, the real
form wins over the data model workbook, which wins over this file -- that
order has already mattered once: the workbook's own indicator list and the
original `parse.py`'s section numbering both turned out not to match the
real form. See `docs/architecture.md`, "Indicator list corrected against the
real reporting forms", before assuming either one is still authoritative on
a point where they conflict.

## What this is

Thirty-one countries return a Word form each quarter. A pipeline parses it,
validates it, computes sixteen indicators and exports static JSON. The site reads
that JSON and draws five screens. Nothing is computed in the browser.

## Repository layout

```
/pipeline
  pyproject.toml        editable install, pytest and ruff config
  src/penplus_pipeline/
    parse.py             reads the .docx returns into records
    validate.py          quality control rules, produces the query register
    load.py              writes the SQLite store, immutable revisions
    transform.py         one function per indicator, producing gold_indicator
    export.py            builds the JSON bundle and the manifest
    seed_history.py      rebuilds historical returns from pre-Phase-Two evidence
    qc.py                standalone query-register tool for an OLDER form version; not wired in
    schema.sql, common.py, penplus.db
  tests/                 pytest suite against synthetic fixtures (see tests/README.md)
/site
  index.html             single entry point
  src/                   TypeScript: lib/, charts/, components/, screens/, styles/
  i18n/                  hand-maintained interface strings, en/fr/pt
  public/data/           the JSON bundle, produced by the pipeline, never hand-edited
  tests/                 vitest suite, screens rendered against the real bundle
/docs                    specification, data model, architecture notes
```

The pipeline stays in flat modules (`parse.py`, not `parse/`) rather than the
package-per-stage layout once sketched here: it was already written and
working this way, and splitting one function per stage into its own package
would have meant a large mechanical rewrite for no behavioural gain. The site
is TypeScript built by Vite rather than hand-written vanilla JS modules --
see "Stack" below for why that still satisfies "no build server required in
production."

## Non-negotiable rules

These come from failures observed in the programme's own data. Breaking one
produces a wrong decision, not an ugly screen.

1. **No arithmetic in the front end.** The site formats, filters and sorts. Every
   indicator value arrives pre-computed with its numerator and denominator. If a
   number has to be derived to draw a chart, derive it in `/pipeline/transform`.
2. **Null is not zero.** A missing figure is `null` end to end, rendered as a gap,
   and excluded from every aggregate. Never `|| 0`, never `?? 0`, never
   `parseInt(x) || 0`. This single idiom is the most likely way to corrupt this
   dashboard.
3. **Never show a rate without n and N.** If the denominator is unavailable, the
   rate is not displayed.
4. **Stock is never summed across periods.** `active_end` and `ever_enrolled` are
   stocks. `new_enrolled`, `ltfu`, `died` are flows. The data model marks which is
   which; no control may offer to sum a stock.
5. **No country ranking.** Distributions and gap to milestone only.
6. **Completeness travels with the figure.** Below 80 per cent the value renders in
   a muted state with the share visible without interaction.
7. **Suppress numerators below five** in anything outside the internal view, and
   flag the suppression rather than blanking silently.
8. **Phase 1 and phase 2 cohorts stay separate** for the first year, and a series
   break is drawn where the condition list or the frequency changed.
9. **Colour never carries meaning alone.** Status vocabulary is exactly: met,
   partly met, not met, not reported.
10. **A country on hold is shown as awaiting clarification**, never as zero and
    never omitted.

## Screens

| # | Screen | The one question it answers |
|---|--------|------------------------------|
| 1 | Regional overview | Where is PEN-Plus and how big is it? |
| 2 | Indicator detail | Is this indicator moving, and who drives it? |
| 3 | Country profile | What is the position of one country? |
| 4 | Data quality | How much of this can be trusted? |
| 5 | Facilities | Where are the sites and what state are they in? |

One screen, one question. If a screen answers two, split it.

## Stack

- Pipeline: Python. `python-docx` for parsing, SQLite for the store, plain
  Python for transformation (one function per indicator, not SQL files --
  see `pipeline/src/penplus_pipeline/transform.py`), plain JSON for export.
- Site: TypeScript compiled and bundled by Vite, charts drawn with Observable
  Plot (SVG, no framework runtime). `vite build` is a build-time step, same
  as any static-site generator; its output is plain HTML/CSS/JS with no
  server process, so "no build server required in production" still holds.
  No UI framework.
- No network calls at runtime beyond same-origin fetches of the bundle. The
  bundle in `/site/public/data` (served at `/data` once built) is the API.
- Target: first meaningful paint under three seconds on a throttled connection.

## Charts

Horizontal bars for comparison across countries. Lines for trend. Dot plots for
distribution. Tables wherever a table is clearer, which is often.

Not allowed: pie charts, donuts, stacked areas, dual axes, gauges, three-dimensional
effects, word clouds, and a choropleth used as the first element of a screen.

## Design tokens

Define tokens before components. One primary colour, WHO institutional navy. One
accent, used only for gap to milestone and alerts. Neutral greys for everything
else. Tabular figures for numbers so columns align. Light mode only, always
readable regardless of the viewer's OS/browser colour-scheme preference.

## Build and test

- `make pipeline` recomputes indicators and re-exports the bundle from the existing
  store. `make rebuild` rebuilds the store from raw evidence in `data/raw/` (not
  included in this repository -- see `docs/architecture.md`).
- `make test` runs both suites: `pytest` against synthetic fixtures in
  `pipeline/tests/` (no real returns exist yet -- every return in the store is
  `historical`), and `vitest` against the real bundle in `site/tests/`. A change
  that alters a published figure must change a fixture and say why.
- Reproducibility is a test: rebuilding from raw returns must reproduce a previously
  published figure exactly. Keep the build manifest with the form version, the data
  model version and the source periods.

## Working preferences

- Small commits, one concern each.
- Ask before adding a dependency.
- No mock data in `/site/data`. Use fixtures in `/tests` instead; mock data has a
  habit of reaching production and being read as real.
- When a rule above makes a screen harder to build, say so rather than working
  around it quietly.

## Out of scope for version 1

Patient-level analysis, live refresh, forecasting, a national-level dashboard,
and any financial figure.


## The pipeline and the site both exist

`/pipeline` is written and runs, and `/site` is built against its bundle.
Read `pipeline/README.md` before touching the pipeline, and
`docs/architecture.md` before assuming any gap you notice is unintentional.

```bash
cd pipeline
pip install -e ".[dev]"
python3 src/penplus_pipeline/run.py --transform --export   # recompute + re-export
python3 src/penplus_pipeline/run.py --returns ../returns/*.docx --transform --export
```

State at the time of writing: 40 returns loaded, 20 countries with data, 5 periods,
367 rows in `gold_indicator`, bundle ~457 KB (`--public`). All 40 are tagged
`source_kind='historical'`, rebuilt from the ICPPA 2026 extraction and the phase 1
monitoring workbook -- no real Phase Two form return has been received yet. The
dashboard makes that distinction visible (`common.historical` chip) and does not draw
a continuous trend across it.

Build the site against this bundle, not against invented data. Where a screen looks
empty, that is the real state of the evidence and the screen must say so rather than
being filled with a placeholder. This includes `dim_indicator.milestone`: it is `null`
for every indicator because the traceability workbook's target values were not part of
this build's source material, and every screen that shows a gap-to-milestone says
"milestone not yet published" rather than fabricating a target.

## Design language

Follow the NCD Population-based Surveillance Intelligence Platform already built for
WHO AFRO: a single self-contained page, numbered tab sections, a hero strip of three
or four headline figures, filter controls above each panel, a CSV export on every
table, and a caption under every chart that states the unit of analysis and how to
read it. The methodology tab is not an afterthought; it is where the limitations of
the data are stated plainly.

Two differences from that platform. There is no composite index here: PEN-Plus
indicators are reported counts, not a score, and inventing an index would manufacture
a ranking the data does not support. And every figure carries its completeness, which
the surveillance platform did not need.
