import { getCountry, getImplementation, getIndicators, getOverview } from "@/lib/bundle";
import { fmtCount, fmtDate, fmtRateWithNandN } from "@/lib/format";
import { t } from "@/lib/i18n";
import { navigate } from "@/router";
import { renderChartPanel } from "@/components/chart-panel";
import { renderValueWithCompleteness } from "@/components/completeness";
import { renderStatus, statusFromGovernance, statusFromImplementationStep, statusKey } from "@/lib/status";
import { facilityStatusKey, projectSupportedKey } from "@/lib/vocab";
import { panelTitleWithIcon } from "@/components/kpi";
import { renderCountryTileBadge } from "@/components/country-tiles";
import { buildTable, tableToCSVData, type Column } from "@/components/table";
import { lineTrend, type TrendPoint } from "@/charts/line";
import type { GoldRow, GovernanceRow, IndicatorDim, OpenQuery } from "@/lib/types";

const PHASE_BREAK_PERIOD = "2026-Q1";
/** Results Framework families, in the form's own focus-area order. */
const FAMILY_ORDER = [
  "governance",
  "service",
  "capacity",
  "quality",
  "workforce",
  "financing",
  "data",
  "communication",
];

function valueText(v: GoldRow): string {
  return v.unit === "rate" ? fmtRateWithNandN(v.numerator, v.denominator, v.value) : fmtCount(v.value);
}

export async function renderCountryProfile(container: HTMLElement, iso3: string): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const [country, indicatorsBundle, implBundle] = await Promise.all([
    getCountry(iso3),
    getIndicators(),
    getImplementation(),
  ]);
  const dimByCode = new Map<string, IndicatorDim>(indicatorsBundle.dim.map((d) => [d.indicator_code, d]));

  // computed ahead of the template so the KPI row can read from it
  const latestPerIndicator = new Map<string, GoldRow>();
  for (const v of country.values) {
    if (v.disagg_key !== "all") continue;
    const prev = latestPerIndicator.get(v.indicator_code);
    if (!prev || v.period_id > prev.period_id) latestPerIndicator.set(v.indicator_code, v);
  }
  const activeInCare = latestPerIndicator.get("2.6");
  const highSeverity = country.open_queries.filter((q) => q.severity === "High").length;

  // Indicators 1.1-1.3 are binary governance milestones, also shown below
  // in the dedicated Governance panel with real provenance (a document
  // name). Design review caught these being shown twice on the same
  // screen, inconsistently: a bare "1"/"0" here, a proper status pill with
  // its supporting document there. Cross-reference to render the identical
  // status pill instead -- keyed on milestone_code, not indicator_code:
  // parse.py's own comment calls 1.1/1.2/1.3 "the fixed codes," and
  // milestone_code carries that exact string throughout the real form
  // parser, historical seeding and the demo generator alike, whereas
  // fact_governance.indicator_code is never actually populated anywhere in
  // the pipeline (checked: parse.py, seed_history.py, generate_demo_bundle.py
  // all leave it unset). A stray non-numeric milestone_code (e.g. the older
  // monitoring-workbook codes like "national_me_framework") never collides
  // with a real indicator_code, so matching directly is safe.
  const govStatusOf = (g: GovernanceRow) => statusFromGovernance(g.status, Boolean(g.document));
  const govByIndicatorCode = new Map(country.governance.map((g) => [g.milestone_code, g]));

  const c = country.country;
  const cohortLabel = t(
    c.cohort === "phase_1" ? "screen1.hero.phase1_legend" : "screen1.hero.phase2_legend",
    {
      n: "",
    },
  ).trim();
  const anyHistorical = country.values.some((v) => v.basis === "historical");
  const activeNull = !activeInCare || activeInCare.value === null;
  const stat = (value: string, label: string, isNull = false) =>
    `<div class="country-hero__stat"><b class="num${isNull ? " is-null" : ""}">${value}</b><span>${label}</span></div>`;

  container.innerHTML = `
    <header class="page-head">
      <h2 class="screen-title">${t("screen3.title")}</h2>
      <p class="panel__question">${t("screen3.question")}</p>
    </header>

    <div class="screen-controls">
      <label>${t("common.select_country")}
        <select id="country-select"></select>
      </label>
    </div>

    <div class="country-hero">
      <div class="country-hero__card">
        <h1 class="country-hero__name">${c.name}</h1>
        <div class="country-hero__chips">
          <span class="chip">${cohortLabel}</span>
          <span class="chip">${t("screen3.chip.returns_on_file", { n: c.returns })}</span>
          ${c.last_period ? `<span class="chip">${t("screen3.chip.last_return", { period: c.last_period })}</span>` : ""}
          ${anyHistorical ? `<span class="chip chip--warm">${t("screen3.chip.historical_evidence")}</span>` : ""}
        </div>
        ${c.returns === 0 ? `<p class="callout callout--empty">${t("screen3.no_return", { country: c.name })}</p>` : ""}
        <div class="country-hero__stats">
          ${stat(fmtCount(country.facilities.length), t("screen3.facilities.title"))}
          ${stat(activeNull ? t("status.not_reported") : fmtCount(activeInCare!.value), t("screen1.hero.active"), activeNull)}
          ${stat(fmtCount(c.returns), t("screen3.kpi.returns"))}
          ${stat(
            String(country.open_queries.length),
            highSeverity > 0 ? t("screen3.kpi.queries_high", { n: highSeverity }) : t("common.open_queries"),
          )}
        </div>
      </div>
      ${renderCountryTileBadge(c.iso3, c.cohort, cohortLabel)}
    </div>

    <div class="indicator-groups" id="indicator-groups"></div>

    <div id="trend-panel"></div>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("target", t("screen3.implementation.title"))}</div>
      <div id="implementation-stepper"></div>
    </section>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("facility", t("screen3.facilities.title"))}</div>
      <div id="facility-table"></div>
    </section>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("flag", t("screen3.governance.title"))}</div>
      <div id="governance-table"></div>
    </section>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("alert", t("screen3.queries.title"))}</div>
      <div id="queries-list"></div>
    </section>
  `;

  // country switcher
  const select = container.querySelector<HTMLSelectElement>("#country-select")!;
  const overview = await getOverview();
  for (const c of [...overview.countries].sort((a, b) => a.name.localeCompare(b.name))) {
    const opt = document.createElement("option");
    opt.value = c.iso3;
    opt.textContent = c.name;
    opt.selected = c.iso3 === iso3;
    select.appendChild(opt);
  }
  select.addEventListener("change", () => navigate({ screen: "country", iso3: select.value }));

  // all sixteen indicators for this country, latest period each (acceptance
  // criterion 3), grouped by Results Framework family -- grouping and
  // ordering only, nothing derived.
  const groupsHost = container.querySelector("#indicator-groups")!;
  const indicatorValue = (d: IndicatorDim): string => {
    const g = govByIndicatorCode.get(d.indicator_code);
    if (g) return renderStatus(govStatusOf(g), t(statusKey(govStatusOf(g))));
    const v = latestPerIndicator.get(d.indicator_code);
    if (!v || (v.value === null && v.suppressed !== 1)) {
      return `<span class="pill pill--nr">${t("status.not_reported")}</span>`;
    }
    return `${renderValueWithCompleteness(valueText(v), v.completeness)} <small>${v.period_id}</small>`;
  };
  for (const family of FAMILY_ORDER) {
    const dims = indicatorsBundle.dim.filter((d) => d.family === family);
    if (dims.length === 0) continue;
    const panel = document.createElement("section");
    panel.className = "panel indicator-group";
    panel.innerHTML = `<h3>${t(`screen3.family.${family}`)} <span class="count">${dims.length}</span></h3>
      ${dims
        .map(
          (d) => `<div class="indicator-row" data-code="${d.indicator_code}">
            <span class="indicator-row__code">${d.indicator_code}</span>
            <span class="indicator-row__label">${d.label_en}</span>
            <span class="indicator-row__value num">${indicatorValue(d)}</span>
          </div>`,
        )
        .join("")}`;
    groupsHost.appendChild(panel);
  }

  // ---- trend for one indicator, chosen from the table above by clicking a row (kept simple: default 2.5)
  const trendCode = latestPerIndicator.has("2.5")
    ? "2.5"
    : (indicatorsBundle.dim[0]?.indicator_code ?? "2.5");
  const dim = dimByCode.get(trendCode);
  if (dim) {
    const series = country.values
      .filter((v) => v.disagg_key === "all" && v.indicator_code === trendCode)
      .sort((a, b) => a.period_id.localeCompare(b.period_id));
    const points: TrendPoint[] = series.map((v) => ({
      period_id: v.period_id,
      value: v.value,
      series: iso3,
      title: `${v.period_id}: ${valueText(v)}`,
    }));
    const crossesBreak =
      series.some((v) => v.period_id < PHASE_BREAK_PERIOD) &&
      series.some((v) => v.period_id >= PHASE_BREAK_PERIOD);
    renderChartPanel(container.querySelector("#trend-panel")!, {
      title: `${t("screen3.trend_since")}: ${dim.label_en}`,
      icon: "trend",
      caption: t("screen2.trend.caption"),
      legendHtml: `<span class="chart-legend__item">${t("common.nr_legend")}</span>`,
      buildChart: () =>
        lineTrend(points, {
          valueLabel: dim.label_en,
          seriesBreakAt: crossesBreak ? PHASE_BREAK_PERIOD : undefined,
          seriesBreakLabel: crossesBreak ? "Phase 1 → 2" : undefined,
        }),
      buildTable: () =>
        buildTable(
          dim.label_en,
          [
            { key: "period_id", label: t("common.select_period"), render: (v: GoldRow) => v.period_id },
            {
              key: "value",
              label: dim.label_en,
              numeric: true,
              html: true,
              render: (v: GoldRow) => renderValueWithCompleteness(valueText(v), v.completeness),
              csv: valueText,
            },
          ],
          series,
        ),
      csv: () =>
        tableToCSVData<GoldRow>(
          [
            { key: "period_id", label: "period_id", render: (v) => v.period_id },
            { key: "value", label: "value", render: (v) => (v.value === null ? "NR" : String(v.value)) },
          ],
          series,
        ),
      csvFilename: `country_${iso3}_${trendCode}_trend`,
    });
  }

  // ---- implementation phase: this country's own row of the fourteen-step
  // stepper (screens/implementation.ts has the full countries x steps grid)
  const stepperHost = container.querySelector("#implementation-stepper")!;
  const highestPhase = country.implementation.highest_phase_completed;
  const highestPhaseText =
    highestPhase === 0 ? t("screen_impl.not_started") : t("screen_impl.phase_n", { n: highestPhase });
  const stepperPhases = [...new Set(implBundle.steps.map((s) => s.phase_no))].sort((a, b) => a - b);
  const markFor = (s: (typeof implBundle.steps)[number]): string => {
    const row = country.implementation.steps.find((r) => r.step_no === s.step_no);
    const status = statusFromImplementationStep(row?.status ?? null);
    const title = [
      `${s.phase_label}: ${s.step_no}. ${s.step_label}`,
      t(statusKey(status)),
      row?.as_of ? `${t("common.as_of")} ${fmtDate(row.as_of)}` : "",
    ]
      .filter(Boolean)
      .join(" · ")
      .replace(/"/g, "&quot;");
    return `<span class="implementation-stepper__mark" title="${title}">${renderStatus(status, String(s.step_no))}</span>`;
  };
  const stepperMarks = stepperPhases
    .map(
      (n) => `<div class="stepper-phase">
        <div class="stepper-phase__marks">${implBundle.steps
          .filter((s) => s.phase_no === n)
          .map(markFor)
          .join("")}</div>
        <small>${t("screen_impl.phase_n", { n })}</small>
      </div>`,
    )
    .join("");
  stepperHost.innerHTML = `
    <p class="chip">${t("screen_impl.column.highest_phase")}: ${highestPhaseText}</p>
    <div class="implementation-stepper">${stepperMarks}</div>
  `;

  // ---- facilities
  const facColumns: Column<(typeof country.facilities)[number]>[] = [
    {
      key: "name",
      label: t("table.facility"),
      // Identity is withheld (name null) in the public export -- fall back
      // to the facility_id rather than let a bare null render as the
      // literal text "null".
      render: (f) => f.name ?? f.facility_id,
    },
    { key: "district", label: t("table.district"), render: (f) => f.district ?? "NR" },
    {
      key: "status",
      label: t("table.status"),
      render: (f) => (f.status ? t(facilityStatusKey(f.status)) : "NR"),
    },
    {
      key: "project_supported",
      label: t("table.project_supported"),
      render: (f) => (f.project_supported ? t(projectSupportedKey(f.project_supported)) : "NR"),
    },
  ];
  container
    .querySelector("#facility-table")!
    .appendChild(
      buildTable(`${country.country.name}: ${t("screen3.facilities.title")}`, facColumns, country.facilities),
    );

  // ---- governance milestones: "a Yes without a document title is not counted"
  const govColumns: Column<GovernanceRow>[] = [
    { key: "milestone", label: t("table.milestone"), render: (g) => g.milestone },
    {
      key: "status",
      label: t("table.status"),
      html: true,
      render: (g) => renderStatus(govStatusOf(g), t(statusKey(govStatusOf(g)))),
      csv: (g) => t(statusKey(govStatusOf(g))),
    },
    { key: "achieved_in", label: t("common.as_of"), render: (g) => g.achieved_in ?? "NR" },
    { key: "document", label: t("table.document"), render: (g) => g.document ?? "NR" },
  ];
  const govHost = container.querySelector("#governance-table")!;
  govHost.appendChild(buildTable(t("screen3.governance.title"), govColumns, country.governance));
  if (country.governance.length === 0) {
    govHost.innerHTML = `<p class="callout callout--empty">${t("empty.no_data")}</p>`;
  }

  // ---- open queries
  const queriesHost = container.querySelector("#queries-list")!;
  if (country.open_queries.length === 0) {
    queriesHost.innerHTML = `<p class="callout callout--empty">${t("common.no_open_queries")}</p>`;
  } else {
    queriesHost.innerHTML = country.open_queries
      .map(
        (q: OpenQuery) => `<div class="callout callout--severity-${q.severity.toLowerCase()}">
        <strong>${q.severity}</strong>, ${q.period_id}, ${q.section} / ${q.field}<br>
        ${q.question}
      </div>`,
      )
      .join("");
  }
}
