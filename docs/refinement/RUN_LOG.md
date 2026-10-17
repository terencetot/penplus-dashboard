# Refinement v2: run log

Run of `docs/refinement/00_START_HERE.md`, stages 1 to 6, done autonomously on branch
`refinement-v2`. Rollback point: tag `pre-refinement-v2` (= `f60a07b`).

## Defaults taken

| # | Decision | Default taken | Why |
|---|---|---|---|
| D1 | Raw workbooks in `docs/refinement/02_data/` | Git-ignored, like `/data/raw/` | The repository is public and `.gitignore` already keeps raw evidence out. The pipeline reads its copies in `data/raw/`. |
| D2 | Stops after each stage | Not taken; stages run back to back | Instruction for this run. |
| D3 | Where the pack's CSVs live for the pipeline | Copied to `data/reference/` and committed | They are curated pipeline inputs (register, phases, query seed, data-system assessment), needed to reproduce the bundle. `docs/refinement/02_data/` keeps the pack as delivered. |
| D4 | Phases reader: country column | Found by its "Countries" header (column C in the real workbook), index 2 as fallback | Robust to the column moving again; the old hard-coded index 3 matched 0 of 20. |
| D5 | Indicator 2.5 for countries that only presented a condition table | Not rebuilt from condition columns: 2.5 is published only where the country gave an all-conditions total (Cameroon, Ethiopia, Mozambique, Zambia) | Which extra conditions count as PEN-Plus is each country's definition. Adding Uganda's asthma or Burkina Faso's 3,402 "HTA" would publish a total no country stated. The condition rows stay visible under 2.5. |
| D6 | 2.6a and 2.6b | Published as companions of 2.6 (sentinel active; approximate retention), like 2.6b already was | The new tool reports ever / new / active / retention under one indicator; the coverage matrix still counts 16 indicators. |
| D7 | Approximate retention scope | Quarterly form returns only, over the conditions with ever, new and active all reported | "Newly enrolled this quarter" has no meaning in a yearly baseline row; a condition missing one figure could push the ratio above 100%. |
| D8 | Rows marked Include = N but of type cumulative / active | Loaded, each as its own year's stock, never added to another year | The flag stops the workbook's own summary from adding years (README caveat f). Loading them gives the real series the audit asks for: Kenya 144 / 347 / 459 / 559 cumulative, Rwanda T1D active 2015-2024. |
| D9 | "as presented (2026 only)" (Burkina Faso, DRC) | Read as point-in-time | A single dated count; not in the README's vocabulary. |
| D10 | Zambia "2.6 active in care, all" (1,328) | Published with 2.5 as "active, all conditions", not as sentinel 2.6a | It covers all PEN-Plus conditions (1,397 ever enrolled); as sentinel it would exceed sentinel ever (1,025) and fail R04. |
| D11 | Zambia "cardiac, not split" (220), Tanzania "sentinel, not split" (558 active) | Counted in the sentinel total as their own unsplit rows | The load map says so ("count in sentinel total only as cardiac, not split"). |
| D12 | Staff trained where the printed total and the cells disagree | The cells | Liberia 407 not 490 (Q-LBR-04), Sierra Leone PIH 2025 13 not 11 (Q-SLE-02), Malawi cadre sums (Q-MWI-02, Medium, so published). The queries stay open. |
| D13 | Indicator 2.3 from the facility register | Only facilities with register status `active`, only at the country's latest baseline period | The register describes June 2026; stamping it on earlier years would invent a history. `partial` (Luwero), `planned` and `to_confirm` are listed, never counted. |
| D14 | Implementation phase | `phase_to_publish` from the reconciliation file; the workbook's 14 steps shown beside it; disagreements flagged (Q-PHS-01). Second-round countries: no phase, "no return yet" | The official map (June 2026) is the more recent source. |
| D15 | Seeded queries the build itself resolves | Closed with a resolution note: Q-REG-02, Q-REG-03, Q-BFA-02, Q-COD-01, Q-UGA-01, Q-KEN-01, Q-NGA-01, Q-SLE-01, Q-COG-01 | Their action is a pipeline or dashboard change made here. Q-COD-01's note says the T1D split must still be requested. All 28 stay in the register. |
| D16 | Q-REG-01 (open, High, scope REG) | Holds every regional patient total (2.5, 2.6, 2.6a, 2.6b); country figures stay published | "Publish none until one figure and its scope are agreed." The overview shows the cards as held with the query id. |
| D17 | Open High query on 2.5 or 2.6 for a country | Holds all of that country's patient figures (2.5, 2.6, 2.6a, 2.6b) | The register predates the new tool's 2.5 / 2.6 split. |
| D18 | A failed High rule | Form return: verdict `hold`. Any return: an open query `V-Rnn-ISO3-period` that holds the indicator it concerns. Held figures are published marked held and kept out of every total | Spec 4.4: "held figures stay out of every published total and are listed on this screen". Previously a held return disappeared from the bundle, indistinguishable from a missing one. |
| D19 | R15 ceiling | 300 T1D patients per active facility (spec default), facilities from 2.3 or, for the baseline, the register | Flags Sierra Leone (639 over 2) and Zimbabwe (3,201 over 4), Medium. |
| D20 | Facility names | Published (`PUBLISH_FACILITY_NAMES = True` in `common.py`); counts under 5 still suppressed | Instruction for this run. |

## Conflicts with CLAUDE.md

| Rule | Pack asks | Resolution |
|---|---|---|
| "Five screens" table | Six screens plus Implementation phases | Not a rule in the non-negotiable list; CLAUDE.md's screens table updated. |
| Rule 1, no arithmetic in the front end | Several new KPI cards and splits | Every count, share and split is computed in `export.py`; the site only formats. |
| Rule 8, cohorts separate | Overview totals across both rounds | The second round has no data, so no total mixes cohorts; provenance rows carry the cohort. |

## Stage 1: readers (commit `8741cb9`)

- `seed_history.from_monitoring_phases` reads the country from the "Countries" column (C). Reads 20 of 20 (was 0).
- Aliases: "Democratic Republic of Congo", "Congo, Republic of", "KEN Kenya".
- `common.TRACERS = ["t1d", "scd", "rhd"]`: severe hypertension out of every sentinel total.
- Facilities are no longer built by splitting "Site or district names".
- Regression tests: `pipeline/tests/test_refinement_stage1.py`.

## Stage 2: new national tool (commit `225bd31`)

- `parse.py` recognises the new tool, keeps reading v3. 2.5 = all PEN-Plus patients; 2.6 = sentinel cohort (ever, new, active); HMIS = 5.2; 5.1 leaves the indicator list.
- The country-entered retention % is never read. `transform.py` computes
  `(active - new) / (ever - new)`, labelled "approximate retention (excludes patients enrolled this quarter)".
- Fixture: the real template filled with synthetic figures (`tests/fixtures/build_national_v4_return.py`). It caught a parser bug: the tool's "Q3" quarter was read as `2026-q3`.

## Stage 3: baseline

- Loaded from `data/raw/PEN-Plus_country_data_ICPPA2026_v2.xlsx` under the "Value type" rules (D8-D12), with deck and slide kept on every value (`gold_indicator.source_ref`, `value_type`).
- Not loaded: Malawi enrolment 2022-2026 (value type unclear, Q-MWI-01); Nigeria staff 2026 (Include = N).
- Facility register (43), phases (31), query seed (28, 9 closed), South Sudan data-system assessment loaded from `data/reference/`.
- `pipeline/tools/reconcile.py` checks every stage 3 expectation against the rebuilt bundle: **all 16 figures and the phase split reproduced; no expectation changed.**

## Skipped

(updated at the end of the run)
