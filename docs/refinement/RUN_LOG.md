# Refinement v2: run log

Run of `docs/refinement/00_START_HERE.md`, stages 1 to 6, done autonomously on branch
`refinement-v2`. Rollback point: tag `pre-refinement-v2` (= `f60a07b`).

## Defaults taken

| # | Decision | Default taken | Why |
|---|---|---|---|
| D1 | Raw workbooks in `docs/refinement/02_data/` | Git-ignored, like `/data/raw/` | The repository is public and `.gitignore` already keeps raw evidence out. The pipeline reads `data/raw/`. The pack's CSVs are committed: they are curated pipeline inputs. |
| D2 | Stops after each stage | Not taken; stages run back to back | Instruction for this run. |

## Conflicts with CLAUDE.md

(none yet)

## Stage log
