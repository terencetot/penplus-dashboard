# PEN-Plus regional dashboard

A regional monitoring dashboard for the WHO AFRO PEN-Plus programme
(Phase Two): where PEN-Plus is delivered, how many patients it reaches and
keeps, whether countries are moving towards their milestones, and how much
of that can be trusted. Built from the quarterly country reporting form.
Static site, no backend, no live feed — the data is quarterly, and a
dashboard that implies otherwise would misrepresent it.

```
returns (.docx) → parse → validate → load → transform → export → static JSON → the dashboard
```

## What's here

- **`pipeline/`** — a Python pipeline that parses completed Word returns,
  runs quality-control checks (arithmetic, cascade, longitudinal), computes
  every indicator, and exports a static JSON bundle. Nothing downstream ever
  computes a figure; the pipeline is the only source of truth for a number.
- **`site/`** — a TypeScript single-page app (built by Vite, charted with
  Observable Plot) that reads that bundle and draws five screens: regional
  overview, indicator detail, country profile, data quality, and facilities.
  No arithmetic happens in the browser.
- **`docs/`** — the technical specification and data model this build was
  contracted against, plus `architecture.md`, which records every place this
  build extends, adapts, or has not yet closed a requirement from them.

## Quick start

```bash
# Pipeline: recompute indicators and re-export the bundle from the store
# already checked into this repo (41 historical returns, 20 countries)
cd pipeline
pip install -e ".[dev]"
python3 src/penplus_pipeline/run.py --transform --export
cd ..

# Site: install, run the tests against the real bundle, and serve it
cd site
npm install
npm test
npm run dev        # http://localhost:5173
```

`npm run build` produces a static `site/dist/` deployable to any file host —
there is no server process to run in production, per the specification's
architecture rule.

**To review the design fully populated:** open the site with `?demo=1`
(e.g. `http://localhost:5173/?demo=1#/overview`), or click "View with demo
data" in the header. Most cells in the real bundle are honestly `NR` today —
no real Phase Two return has been submitted yet — which is correct but makes
layout and density hard to judge. Demo mode swaps in a wholly synthetic,
fully-populated bundle (`pipeline/tools/generate_demo_bundle.py`, output at
`site/public/demo-data`) with a permanent on-screen banner while it's on, and
never touches the real bundle. Turn it off with "Exit demo mode" or `?demo=0`.

## Why this stack

The specification is explicit and this build follows it rather than
defaulting to whatever is fashionable:

| Layer | Choice | Why |
|---|---|---|
| Pipeline | Python, SQLite, `python-docx` | Named directly in the specification; already written and tested against the reporting form. |
| Site | TypeScript, Vite, Observable Plot | The spec asks for "vanilla JavaScript or a light framework... no build server required in production." A `vite build` is a build-**time** step producing plain static files — no different in kind from any static-site generator — so it satisfies that constraint while giving strict types, a real module system, and a small SVG charting library instead of hand-rolled DOM code. No UI framework. |
| Data bundle | Static JSON, one file per screen | "No backend to run, host or secure; the bundle is the API." |

See `docs/architecture.md` for the full reasoning, including three real gaps
found and closed in the pipeline this build inherited (no validation stage
was actually wired in, `dim_indicator` had no milestone column despite the
data model requiring one, and a hard-coded environment path in `run.py`).

## The rules this build is not allowed to break

These come directly from the specification and from failures observed in
comparable programmes — breaking one produces a wrong decision, not just an
ugly screen:

1. **No arithmetic in the front end.** Every figure arrives pre-computed with
   its numerator and denominator.
2. **Null is not zero.** A missing figure is `null` end to end, rendered as a
   gap, and excluded from every aggregate.
3. **Never a rate without n and N.**
4. **Stock is never summed across periods.**
5. **No country ranking** — distribution and gap to milestone only.
6. **Completeness travels with the figure**, muted below 80%.
7. **Suppress numerators below five** outside the internal view, flagged, never
   blanked.
8. **Phase 1 and Phase 2 cohorts stay separate** for the first year, with a
   drawn series break at the transition.
9. **Colour never carries meaning alone** — status is always a label plus a
   mark, from exactly four states: met, partly met, not met, not reported.
10. **A country on hold is shown as awaiting clarification**, never as zero,
    never omitted.

Full detail in `CLAUDE.md` and `docs/specification.md`.

## Known limitations

Stated plainly, in the spirit of the project's own rule that an empty screen
should say why rather than being filled with a placeholder:

- **No milestone targets are populated.** `dim_indicator.milestone` is `null`
  for every indicator; the traceability workbook that holds those numbers
  was not part of this build's source material. Every screen that would show
  a gap-to-milestone says so explicitly instead of drawing a bar against a
  fabricated target.
- **The indicator list was corrected against the real reporting forms.**
  This build originally trusted the data model workbook's shorter,
  differently-coded indicator list; once the actual
  `Phase_2_PEN-Plus_Reporting_Tools.docx` (v3) became available it turned
  out neither that list nor the parser's section numbering matched the real
  form. All sixteen real indicators are now computed into `gold_indicator`.
  See `docs/architecture.md`, "Indicator list corrected against the real
  reporting forms", for the full account, including two country-reported
  aggregates (2.2/2.3/2.4/3.4's own summary tables, and 5.1's HMIS
  integration level) that are captured but not yet folded into a published
  rate — the bottom-up, Annex-A-derived figures are used instead.
- **Screen 1's "map" is a grid of country tiles, not a geographic map.** No
  licensed AFRO boundary file was available, and an unverified one was not
  worth the risk of drawing wrong or disputed borders.
- **One bundle, not an internal/public split.** The specification calls for
  facility-level detail to be internal-only, with a suppressed, aggregated
  public view. This build produces a single bundle at facility grain. See
  "Before you publish this repository" below.
- **No real Phase Two return has been received yet.** Every return in the
  store is `source_kind='historical'`, rebuilt from the ICPPA 2026 extraction
  and the Phase 1 monitoring workbook. The dashboard marks this explicitly
  and does not draw a continuous trend across the boundary.

## Before you publish this repository

Read this before making the repository (or its hosted site) public.

`pipeline/src/penplus_pipeline/penplus.db` and `site/public/data/facilities.json`
carry facility-level detail — names, districts, status — for real PEN-Plus
sites. The specification's own security section reserves that grain for the
**internal view**: "Facility-level figures are visible in the internal view
only. The public view aggregates to district or country and applies
suppression." This build has not implemented that split, so a public copy of
this repository (or a public deployment of `site/dist/`) currently exposes
facility-level data the specification says should not be public. Options, in
order of effort: keep the repository private; strip `facilities.json` and
`penplus.db` from a public copy and regenerate a country-level-only bundle;
or implement the internal/public bundle split before publishing openly.

## Testing

```bash
make test          # both suites
make test-pipeline # pytest, synthetic fixtures (pipeline/tests/README.md explains why)
make test-site     # vitest, screens rendered against the real bundle in site/public/data
```

32 pipeline tests and 30 site tests pass at the time of writing, including
the two acceptance-criteria checks that motivated the validation stage: a
deliberate arithmetic error is held and appears in the query register, and a
held return never reaches `gold_indicator`.

## License

See [LICENSE](LICENSE).
