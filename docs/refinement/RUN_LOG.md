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

## Stage 4: facilities and map (commit `945d69c`)

- `scripts/geocode_facilities.py` follows `GEOCODING_PROTOCOL.md`: Nominatim, one request per second, every response cached in `data/geocode_cache.json` (98 requests), review table `data/geocode_review.csv`.
- **11 of 43** facilities pass every rule and are mapped (`geo_checked = auto`): Phebe, C.B. Dunbar, Tellewoyan (Liberia, still status *to confirm*, Q-LBR-03), Wuse General (Nigeria), Kirehe District (Rwanda), Koidu and Pujehun Government (Sierra Leone), Karatu Lutheran (Tanzania), Atutur General (Uganda), Matero Level 1 (Zambia), Ndanga District (Zimbabwe). All are within 5.3 km of their town.
- 21 town points (not shown) and the rest are listed as **location to confirm**. Chipata (Q-ZMB-02) was not geocoded.
- Facilities screen: KPI row, map (shape by status, never size or colour by performance, WHO disclaimer), register with names, partner, status, conditions, the patient figure printed on the slide and its source.

## Stage 5: screens (commits `8cff6bb`, `153d4d2`)

- Banner on every screen while no validated return exists: "Baseline from country presentations at ICPPA 2026 (June 2026), not yet validated quarterly returns."
- Overview: facilities, sentinel patients (2.6), all-conditions patients (2.5), sentinel active (2.6a), health workers trained (3.3 to date). The three regional patient totals show **Held · Q-REG-01** with their country coverage. Every country is listed with its phase, or "No return yet".
- Indicator detail: value type, source slide and provenance on every value. Held figures are drawn as an outline labelled "Held". Trend lines appear only where three or more periods exist: Kenya, Liberia, Sierra Leone and Uganda (2.6); Rwanda (2.6a).
- Country profile: map tile, then name with cohort, phase and provenance chips, then coat of arms (off). Below: the register's facilities, every query, and the data-system card where one exists.
- Implementation phases: published phase, the workbook's 14 steps, disagreements flagged. 11 second-round countries show "No return yet".
- Data quality, rebuilt to `DATA_QUALITY_SPEC.md`:
  - KPI row with n of N;
  - provenance for all 31 countries (Validated / Not validated / Held / No return yet);
  - 31 × 16 coverage matrix;
  - R01-R17 with passed / failed / not testable;
  - held figures;
  - query register with filters and CSV export;
  - South Sudan data-system card. No respondent names are published.

## Stage 6: design

- `05_design/tokens.penplus.additions.css` appended to `tokens.css` unchanged (condition, cohort, provenance and country-identity tokens). No ICPPA branding.
- Country assets: `site/src/config.ts` (`SHOW_COAT_OF_ARMS = false`, `COUNTRY_ASSETS = {}`). Each falls back gracefully: the ISO3 tile for a missing map, nothing for missing arms, no request for a file that is not listed.
- Screenshots: `docs/refinement/screenshots/`, every screen at 1440 px and 390 px (14 files). I reviewed all of them against the audit:
  - no "not started" for missing data, and no "Accepted";
  - no "0 open queries" (21 open: 3 High, 11 Medium, 7 Low);
  - all 31 countries on the overview, data quality and implementation screens;
  - no severe hypertension in any sentinel total;
  - no horizontal scroll at 390 px;
  - no page errors.
- Issues found by that review and fixed:
  - "as of" showed the build date; it now shows the ICPPA evidence cut-off, 30 June 2026;
  - "KEN Kenya" showed as a display name (an alias listed first);
  - 3.3 was labelled "enrolled" instead of "trained";
  - five phone-width overflows.

## Published figures that changed

Country figures, latest period. "Old" is the bundle of `pre-refinement-v2`, where 2.5 meant priority-condition patients ever enrolled. Source slides are in `06_evidence_slides/`.

| Country | Old (2.5) | New | Why | Source |
|---|---:|---|---|---|
| Uganda | 2,241 | 2.6 = 2,226 | Severe HTN 15 left the sentinel total (Q-REG-02, Q-UGA-01) | D3M p254 |
| Burkina Faso | 3,902 | 2.6 = 500 (SCD) | "HTA" 3,402 is not a sentinel condition (Q-BFA-02) | D2M p211 |
| DRC | 570 | 2.6 = 7 (SCD) | "HTA" 563 out; T1D still merged with T2D (Q-COD-01) | D2M p241 |
| Zimbabwe | 4,590 | 4,590, **held** | Open High query Q-ZWE-01: case definition | D3K p76 |
| Sierra Leone | 1,829 | 2.6 = 1,829 | Unchanged | D3M p224, p225 |
| Liberia | 90 | 2.6 = 90 | Unchanged | D3M p241 |
| Kenya | (none) | 2.6 = 559 (T1D 310) | Added in extraction v2; cumulative, not summed | D2K p93 |
| Tanzania | (none) | 2.6a = 558 active | Load map | D2M p51 |
| Ethiopia | (none) | 2.5 = 865 | Load map | D3M p266 |
| Mozambique | (none) | 2.5 = 254 | Load map | D3K p36 |
| Zambia | (none) | 2.5 = 1,397; 2.6 = 1,025 (SCD 712, T1D 93, cardiac not split 220) | Load map | D3M p200-201 |
| Cameroon | (none) | 2.5 = 130; 2.6 = 38 | Load map | D2M p228 |
| Ghana | (none) | 2.6 = 46 (T1D) | Load map | D3K p62 |
| Republic of the Congo | (none) | 2.6 = 4 (SCD) | Load map | D2M p256 |
| Rwanda | (none) | 2.6a = 2,847 T1D active (2024) | Active series, not summed | D3K p51 |

Health workers trained (3.3, since the programme began): newly published for 12 countries, 2,419 in total:

| Country | Trained | Source |
|---|---:|---|
| Malawi | 1,121 (cell sums, Q-MWI-02) | D2K p80 |
| Liberia | 407 (not 490, Q-LBR-04) | D3M p241 |
| Ghana | 369 | D3K p60 |
| Kenya | 198 | D2K p90 |
| Sierra Leone | 93 | D3M p224-225 |
| DRC | 54 | D2M p241 |
| Uganda | 50 | D3M p255 |
| Burkina Faso | 43 | D2M p213 |
| Zimbabwe | 33 | D3K p73 |
| Republic of the Congo | 20 | D2M p254 |
| Cameroon | 17 | D2M p223 |
| Ethiopia | 14 | D3M p265 |

Regional and screen-level figures:

| Figure | Old | New |
|---|---|---|
| Facilities providing services (2.3) | 31 in 15 countries | 33 in 15 countries (register, active only) |
| Patients ever enrolled (regional) | 13,222 (6 countries) | Held, Q-REG-01 (sentinel: 10 countries; all conditions: 4) |
| Patients active in care | Not reported | Held, Q-REG-01 (2 countries) |
| Health workers trained | Not reported | 2,419 (12 countries) |
| Countries that published at least one figure | 20 of 31 | 17 of 31 (non-null values only) |
| Implementation phases | 0 with phase data, 31 "not started" | Phase 5: 1, phase 4: 15, phase 3: 3, phase 2: 1, no return yet: 11 |
| Open queries | 0 | 21 (3 High), plus 9 closed by this build |
| Completeness "0 below 80%" | shown | removed: not measurable without form returns |

## More defaults taken in stages 4 to 6

| # | Decision | Default |
|---|---|---|
| D21 | Geocoding region rule | A match on the register's own admin2 district counts as "inside the stated region": OpenStreetMap files Sierra Leone's hospitals under "Kono District", not "Eastern Province". |
| D22 | Map boundaries | None drawn. WHO-cleared boundaries were not provided and no boundary file was added. Points sit on a longitude / latitude graticule with the WHO disclaimer. |
| D23 | Coat of arms | Off (`SHOW_COAT_OF_ARMS = false`). Country map and arms files were not in the pack, so every profile uses its ISO3 tile. |
| D24 | Cohort names | "First / second HCT round" instead of "Phase 1 / 2 cohort", as in the design brief. "Phase" now means only the five implementation phases. |
| D25 | Default indicator on screen 2 | 2.6 (sentinel), the series with the most country evidence. |
| D26 | Date of an undated baseline row | 30 June 2026, the ICPPA evidence cut-off. |
| D27 | Decorative tile map at phone width | Hidden below 640 px. It encodes cohort only, which the lists below repeat. |
| D28 | CI and deploy guard "no facility identity in the public bundle" | Now follows the bundle's `publish_facility_names` flag (the old guard blocked the first merge). A new check fails the build if any suppressed cell (under 5) is published with its number. |

## Skipped

- **Malawi enrolment** (value type unclear, Q-MWI-01) and **Nigeria staff 2026** (Include = N): not loaded, by the workbook's own rules.
- **Country maps and coats of arms**: no files in the pack. The hooks exist (`site/src/config.ts`); add the files and list them there.
- **WHO-cleared map boundaries**: not available (D22).
- **Team decisions in `00_START_HERE.md`** were not taken: Q-REG-01 regional headline, the 7 High queries, the retention formula, and GPS / DHIS2 UID in Annex A. The dashboard shows each as open.
- **`make`** is not installed on this Windows machine. `make test` was run as its two halves: `cd pipeline && python -m pytest` (92 passed) and `cd site && npm test` (52 passed). Ruff, ESLint, `tsc`, Prettier and `vite build` all pass with no warnings.
- **ICPPA branding**: none used, by the design brief.
