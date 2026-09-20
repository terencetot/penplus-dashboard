# PEN-Plus regional dashboard — technical specification

> Transcribed from `PEN-Plus_Dashboard_Specification.docx` (version 1.0, for
> build) for readability and diffability in version control. The original
> `.docx` is kept alongside this file; where the two differ, the `.docx` is
> authoritative.

**Source of truth:** PEN-Plus quarterly country report, version 3.0, and the
traceability workbook.
**Build environment:** Claude Code, static site, no server-side runtime.

## 1. What the dashboard is for

The dashboard answers four questions and nothing else: where PEN-Plus is
being delivered, how many patients it reaches and keeps, whether countries
are moving towards their milestones, and how much of that can be trusted.
Anything that does not serve one of those four is out of scope.

It is not a data entry tool, not a national monitoring system, and not a
substitute for DHIS2. Countries monitor their own programmes in their
national platform. This is the regional layer, built from the quarterly
country returns.

### Audiences, in priority order

| Audience | The question they arrive with | What they must be able to do in under a minute |
|---|---|---|
| WHO AFRO NCD and Mental Health team | Are the sixteen indicators moving towards the milestones? | See the gap to milestone for every indicator, and which countries drive it |
| Regional leadership and Regional Committee | What has the Region achieved with PEN-Plus? | Read four headline figures with their date, coverage and completeness |
| Partners and funders | Is the investment producing patients in care? | See patients reached and retained, split by project-supported sites |
| National programmes and WHO country offices | How does my country compare, and what is outstanding from me? | Open a country profile and see its own figures and any pending query |

## 2. Screens

Five screens. One screen answers one question. If a screen answers two, it
becomes two screens.

| # | Screen | The one question | Core content | Refresh |
|---|---|---|---|---|
| 1 | Regional overview | Where is PEN-Plus and how big is it? | Four headline figures with completeness flag; map of countries by phase and status; milestone progress strip for the five headline indicators | Quarterly |
| 2 | Indicator detail | Is this indicator moving, and who drives it? | One indicator, all countries: distribution, trend, gap to milestone, numerator and denominator on hover, definition panel | Quarterly |
| 3 | Country profile | What is the position of one country? | All sixteen indicators for one country, trend since first return, completeness and confidence, facility list, outstanding queries | Quarterly |
| 4 | Data quality | How much of this can be trusted? | Reporting completeness and timeliness by country and period, confidence declarations, open queries, definition compliance | Quarterly |
| 5 | Facilities | Where are the sites and what state are they in? | Facility table and map from Annex A: status, readiness class, quality score, mentorship, patients | Quarterly |

### Screen 1 in detail

The four headline figures are: countries implementing, PEN-Plus facilities
providing services, patients ever enrolled, patients active in care. Each
carries the period it refers to and the share of expected facility returns
behind it. A headline figure without its completeness is not displayed.

The milestone strip shows, for the five headline indicators, the last value,
the milestone and the gap, as a horizontal bar against a target marker. Not
a gauge, not a dial, not a traffic light.

## 3. Display rules

These rules are not stylistic. Each one exists because breaking it has
produced a wrong decision in a comparable programme.

1. **Never a rate without its denominator.** Every percentage displays n and
   N on the element or on hover. A rate built on fewer than twenty patients
   is shown with its confidence interval.
2. **Never a country league table.** Show the distribution and the gap to
   milestone. Ranking thirty countries on figures of unequal completeness
   manufactures a hierarchy out of reporting behaviour.
3. **NR is not zero.** A non-response is drawn as a gap, never as a zero
   point, and a line chart breaks rather than joins across it. The legend
   names NR explicitly.
4. **Completeness travels with the figure.** Every aggregate carries the
   share of expected facility returns behind it. Below 80 per cent the
   figure is displayed in a muted state with the share visible without
   interaction.
5. **Suppress small cells in any view that leaves the Regional Office.**
   Cells with fewer than five patients are suppressed and flagged as
   suppressed, never replaced by zero.
6. **Cohorts are not mixed in the first year.** The twenty Phase 1 countries
   and the eleven Phase 2 countries are shown as distinct cohorts until the
   second annual reporting round.
7. **Series breaks are drawn.** The Phase 1 to Phase 2 transition changed the
   condition list and the frequency; the chart shows a marked discontinuity
   and the tooltip says what changed.
8. **Colour never carries meaning alone.** Status is always accompanied by a
   label or a mark. Met, partly met, not met, not reported, in that
   vocabulary.
9. **Stock and flow are never summed.** Patients active in care is a stock
   taken at period end. Newly enrolled is a flow. The data model enforces
   this; the interface must not offer a control that breaks it.
10. **Every figure states its as-of date and the definition applied.**
    Retention built on a sixty-day rule is labelled as such and excluded
    from the regional aggregate.

## 4. Data flow

The dashboard reads pre-computed files. It performs no calculation of its
own beyond formatting, filtering and sorting. Any arithmetic in the front
end is a second source of truth and will diverge.

| Stage | What happens | Output | Owner |
|---|---|---|---|
| 1. Return received | A country returns the Word form, named `ISO3_YEAR_PERIOD_PENPLUS.docx` | Raw file, stored immutably with a checksum | Regional M&E |
| 2. Parse | The parser reads the tables by position and row label into records | One JSON record set per return | Data engineer |
| 3. Validate | The quality control rules run: arithmetic, cascade, longitudinal, plausibility | Query register and a pass, hold or query verdict | Automated, reviewed by M&E |
| 4. Load | Validated records are written to the store, versioned, never overwritten | Bronze and silver tables | Data engineer |
| 5. Compute | Indicator formulas from Annex B of the form are applied | Gold indicator table, one row per country, period, indicator, disaggregation | Analytics engineer |
| 6. Publish | Gold tables are exported as static JSON with a build manifest | Dashboard data bundle | Build pipeline |
| 7. Render | The site reads the bundle and draws the screens | The dashboard | Front end |

A return that fails validation with a high severity finding never reaches
stage 5. It is held and queried. The dashboard shows the country as awaiting
clarification rather than showing a wrong figure, and that state is itself
informative.

## 5. Architecture

| Layer | Choice | Why | Alternative if constrained |
|---|---|---|---|
| Parser | Python with `python-docx` | Already written and tested against the form; reads drop-down content controls | None; the form is the contract |
| Store | SQLite or PostgreSQL | Thirty-one countries by four quarters is small; a relational store is sufficient and portable | DuckDB with Parquet files |
| Transformation | SQL held in version control, one file per indicator | Every indicator has one implementation, auditable and testable | R or Python scripts organised as a package |
| Data bundle | Static JSON, one file per screen, plus a manifest with the build date and the source periods | No backend to run, host or secure; the bundle is the API | CSV if JSON is refused |
| Front end | Single-page static site, vanilla JavaScript or a light framework, charts drawn with a small library | Runs anywhere, loads fast on a constrained connection, no build server required in production | Any framework the team maintains |
| Hosting | WHO AFRO infrastructure, internal view behind authentication, public view with suppression applied | Data sovereignty and suppression obligations | Internal only, with PDF exports for external sharing |
| Refresh | Rebuilt on each publication round, not continuously | The data is quarterly; a live feed implies a currency the data does not have | None |

## 6. Design system

- One primary colour, WHO institutional navy, and one accent used only for
  gap to milestone and for alerts. Colour is never decorative.
- Status vocabulary, used everywhere: met, partly met, not met, not
  reported. Four states, four marks, never more.
- Typography: a single family, three sizes for figures, labels and body.
  Numbers set in tabular figures so columns align.
- Charts: horizontal bars for comparison across countries, lines for trend,
  dot plots for distribution. No pie charts, no stacked areas, no dual axes,
  no three-dimensional effects.
- The map situates, it does not rank. It is never the first element of a
  screen, and it carries no colour scale that implies performance.
- Every screen has a print and PDF export, because review meetings happen
  without connectivity.
- Interface strings come from the indicator registry, in English, French and
  Portuguese. No string is translated inside a component.

## 7. Accessibility and performance

- Contrast ratio of at least 4.5 to 1 for text, and no information conveyed
  by hue alone.
- Fully operable by keyboard; every chart has a table equivalent reachable
  without a mouse.
- First meaningful paint under three seconds on a 3G connection. The data
  bundle for one screen stays under 500 kilobytes.
- The site degrades to readable tables if scripting fails.

## 8. Security and data protection

- No patient-level data reaches the dashboard. The finest grain published is
  the facility.
- Facility-level figures are visible in the internal view only. The public
  view aggregates to district or country and applies suppression.
- The internal view is authenticated and access is reviewed every six months
  against a named list.
- No country figure appears in any view before the national programme has
  seen it. The publication step includes a hold flag that the Regional
  Office clears per country.

## 9. Acceptance criteria

The build is accepted when all of the following are demonstrated on real
returns, not on synthetic data.

1. A completed Word return is parsed, validated and rendered on the
   dashboard without a single manual transcription.
2. A return with a deliberate arithmetic error is held, appears in the query
   register, and does not change any published figure.
3. Every one of the sixteen indicators displays its numerator, denominator,
   definition and as-of date.
4. A country with 40 per cent reporting completeness is visibly
   distinguishable from a country at 100 per cent, without interaction.
5. An NR value is drawn as a gap in a trend line, and the same value is not
   counted as zero in any aggregate.
6. No view accessible outside the Regional Office exposes a cell with fewer
   than five patients.
7. The Phase 1 to Phase 2 series break is marked on every trend that crosses
   it.
8. Each screen loads in under three seconds on a throttled connection and
   exports to PDF.
9. Rebuilding from the raw returns reproduces a previously published figure
   exactly.

## 10. Out of scope for version 1

- Patient-level analysis of any kind, including survival curves and
  determinants of attrition. That requires the facility data layer and a
  separate governance decision.
- Live or near-real-time refresh. The data is quarterly.
- Forecasting and projection. Worth doing, but only once four consecutive
  comparable rounds exist.
- A national-level dashboard. Countries use their own platform; duplicating
  it creates a competing source of truth.
- Financial figures. Removed from the reporting form and therefore absent
  here.

---

See `docs/architecture.md` for how this build satisfies, adapts, or has not
yet closed each of these requirements.
