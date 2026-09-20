# PEN-Plus pipeline

Turns completed Word country returns into a SQLite store and a static JSON bundle
for the dashboard. No manual transcription anywhere in the chain.

```
returns (.docx) -> parse -> validate -> load -> transform -> export -> site/public/data/*.json
```

## Quick start

```bash
pip install -e ".[dev]"                          # from pipeline/, installs python-docx, openpyxl, pytest, ruff
python3 src/penplus_pipeline/run.py --transform --export     # recompute + re-export from the existing store
python3 src/penplus_pipeline/run.py --returns ../returns/*.docx --transform --export
```

`--rebuild` (`--fresh --seed --transform --export`) deletes the store and reloads it
from the historical evidence workbooks in `data/raw/` (see "Seeding" below) --
it needs those two files, which are not part of this repository. Day to day,
`--transform --export` against the store already checked into this repo (`penplus.db`)
is the command to run when a formula changes.

## Files

| File | What it does |
|------|--------------|
| `schema.sql` | The store. Grain and nullability follow the data model workbook. |
| `common.py` | Country list with ISO3 and cohort, condition and cadre maps, indicator register. |
| `parse.py` | Reads a completed form. Tables located by heading, rows by label, never by index. |
| `validate.py` | Arithmetic, cascade and longitudinal checks. Writes the query register and decides accepted / query / hold. |
| `load.py` | Writes a return. Immutable: a re-load creates a revision and supersedes the old one. |
| `seed_history.py` | Rebuilds returns from the ICPPA extraction and the phase 1 monitoring workbook. |
| `transform.py` | One implementation per indicator, writing `gold_indicator`. |
| `export.py` | The JSON bundle, one file per screen plus a manifest. |
| `run.py` | The whole chain in one command. |
| `qc.py` | A standalone query-register tool for an **older** form version (different section numbering). Not wired into the chain above -- see `docs/architecture.md`. |

## Validation

A parsed return is checked before it is loaded: the patient cascade
(`active_end` cannot exceed `ever_enrolled`), the age-band reconciliation
(the age bands must sum to `active_end`), the longitudinal rule
(`ever_enrolled` must never decrease from the previous period), and
completeness/retention arithmetic. Any High-severity finding sets
`verdict='hold'` -- `transform.py` excludes held returns from
`gold_indicator` entirely, so a bad return is queried, never published.
Every finding, High or not, is written to `query_register` and reaches the
dashboard's data-quality screen and the country's open-queries list.

## The rules the code enforces

- **NULL is never zero.** A cell reading NR parses to `None`, stays `None` through
  the store, and is excluded from every sum. `_sum` returns `None` when every input
  is `None`, so a country that reported nothing never appears as a genuine zero.
- **Stock is never summed across periods.** `ever_enrolled` and `active_end` are
  stocks; `new_enrolled` and the exit columns are flows. The tables are separate so
  the distinction cannot be lost in a join.
- **Only the four tracer conditions enter the regional total.** Everything else is
  carried as `other_reported` and reported separately.
- **Retention is excluded where the regional ninety-day rule was not applied.**
  `ltfu_compliant` gates indicator 2.6b.
- **Returns are immutable.** A correction is a new revision; the old one is marked
  superseded and kept. A published figure can always be reproduced.
- **Historical returns are labelled.** `source_kind='historical'` and a provenance
  string, so a figure rebuilt from ICPPA slides is never mistaken for a country
  return on the form.

## Seeding from what exists today

There are no completed Phase Two returns yet, so the store is seeded from two real
sources, converted into returns of the same shape:

- **ICPPA 2026 country data extraction** gives patients by year and condition, staff
  trained by year and cadre, and the site lists. Year rows are loaded as flows; the
  cumulative stock is the running sum, not a figure lifted from a slide.
- **PEN_PLUS_MONITORING.xlsx** gives the districts implementing PEN-Plus and the
  pillar activities, read as governance milestones.

Both are tagged `historical`. The dashboard must show them as such, and must not
draw a continuous trend across the boundary with the first real Phase Two return.

## Adding a real return

```bash
python3 src/penplus_pipeline/run.py --returns ZMB_2026_Q3_PENPLUS.docx --transform --export
```

A return whose tables have been restructured is rejected with a message naming the
problem, and nothing is loaded. That is deliberate: a half-read return is worse than
a rejected one. A return that parses but fails validation is held, not rejected --
it is written to the store with `verdict='hold'` and its findings, and stays out of
`gold_indicator` until it is corrected and re-loaded as a new revision.

## Tests

```bash
python3 -m pytest -v            # from pipeline/
```

All fixtures are synthetic (see `tests/README.md`): no real Phase Two return has
been received yet, and the historical evidence is aggregate-level, not row-level, so
neither can stand in for a realistic `.docx` fixture. `tests/fixtures/build_synthetic_return.py`
builds one programmatically, matching the structure `parse.py` expects.
