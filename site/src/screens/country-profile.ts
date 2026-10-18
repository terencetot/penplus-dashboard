import { getCountry, getImplementation, getIndicators, getOverview } from "@/lib/bundle";
import { fmtCount, fmtDate, fmtRateWithNandN } from "@/lib/format";
import { t } from "@/lib/i18n";
import { navigate } from "@/router";
import { renderChartPanel } from "@/components/chart-panel";
import { renderValueWithCompleteness } from "@/components/completeness";
import { renderStatus, statusFromGovernance, statusFromImplementationStep, statusKey } from "@/lib/status";
import { panelTitleWithIcon } from "@/components/kpi";
import { renderCountryTileBadge } from "@/components/country-tiles";
import { buildTable, tableToCSVData, type Column } from "@/components/table";
import { provenanceOf, renderProvenance, renderSourceRef, valueTypeLabel } from "@/components/provenance";
import { renderQueryList } from "@/components/queries";
import { lineTrend, type TrendPoint } from "@/charts/line";
import { COUNTRY_ASSETS, SHOW_COAT_OF_ARMS } from "@/config";
import type { FacilityRow, GoldRow, GovernanceRow, IndicatorDim } from "@/lib/types";

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
/** The trend shown on the profile: the first of these with a series. */
const TREND_PREFERENCE = ["2.6", "2.6a", "2.5", "3.3"];

function valueText(v: GoldRow): string {
  return v.unit === "rate" ? fmtRateWithNandN(v.numerator, v.denominator, v.value) : fmtCount(v.value);
}

/**
 * Screen 3: "What is the position of this country?" Header with the country
 * map (its ISO3 tile until a map file is added), name and chips (cohort,
 * phase, provenance), coat of arms behind SHOW_COAT_OF_ARMS. Every figure
 * carries its value type, source slide and provenance mark.
 */
export async function renderCountryProfile(container: HTMLElement, iso3: string): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const [country, indicatorsBundle, implBundle, overview] = await Promise.all([
    getCountry(iso3),
    getIndicators(),
    getImplementation(),
    getOverview(),
  ]);
  const dimByCode = new Map<string, IndicatorDim>(indicatorsBundle.dim.map((d) => [d.indicator_code, d]));

  const latestPerIndicator = new Map<string, GoldRow>();
  const latestToDate = new Map<string, GoldRow>();
  for (const v of country.values) {
    const target =
      v.disagg_key === "all"
        ? latestPerIndicator
        : v.disagg_key === "measure" && v.disagg_value === "to_date"
          ? latestToDate
          : null;
    if (!target) continue;
    const prev = target.get(v.indicator_code);
    if (!prev || v.period_id > prev.period_id) target.set(v.indicator_code, v);
  }

  const govStatusOf = (g: GovernanceRow) => statusFromGovernance(g.status, Boolean(g.document));
  const govByIndicatorCode = new Map(country.governance.map((g) => [g.milestone_code, g]));

  const c = country.country;
  const impl = country.implementation;
  const cohortLabel = t(c.cohort === "phase_1" ? "common.phase1" : "common.phase2");
  const openQueries = country.queries.filter((q) => q.status === "open");
  const highSeverity = openQueries.filter((q) => q.severity === "High").length;
  const activeFacilities = country.facilities.filter((f) => f.register_status === "active").length;

  const assets = COUNTRY_ASSETS[c.iso3] ?? {};
  const base = import.meta.env.BASE_URL;
  const mapHtml = assets.map
    ? `<img class="country-hero__map" src="${base}assets/countries/${c.iso3}/${assets.map}" alt="${t("screen3.map_alt", { country: c.name })}" />`
    : renderCountryTileBadge(c.iso3, c.cohort, cohortLabel);
  const armsHtml =
    SHOW_COAT_OF_ARMS && assets.arms
      ? `<img class="country-hero__arms" src="${base}assets/countries/${c.iso3}/${assets.arms}" alt="${t("screen3.arms_alt", { country: c.name })}" />`
      : "";

  const stat = (value: string, label: string, sub = "", isNull = false) =>
    `<div class="country-hero__stat"><b class="num${isNull ? " is-null" : ""}">${value}</b><span>${label}</span>${sub ? `<small>${sub}</small>` : ""}</div>`;
  const patientStat = (code: string, label: string) => {
    const v = latestPerIndicator.get(code);
    if (!v || v.value === null) return stat(t("status.not_reported"), label, "", true);
    const sub = `${valueTypeLabel(v.value_type, v.as_of, v.indicator_code)} ${renderSourceRef(v.source_ref)}${v.held ? ` ${renderProvenance("held", v.held_by)}` : ""}`;
    return stat(fmtCount(v.value), label, sub);
  };

  const phaseChip =
    impl.phase !== null
      ? `<span class="phase-chip phase-chip--${impl.phase}">${t("screen_impl.phase_n", { n: impl.phase })}</span>`
      : `<span class="prov prov--no_return">${t("prov.no_return")}</span>`;

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
      <div class="country-hero__identity">${mapHtml}</div>
      <div class="country-hero__card">
        <div class="country-hero__titlerow">
          <h1 class="country-hero__name">${c.name}</h1>
          ${armsHtml}
        </div>
        <div class="country-hero__chips">
          <span class="chip chip--cohort-${c.cohort}">${cohortLabel}</span>
          ${phaseChip}
          ${renderProvenance(country.provenance.status)}
          ${c.last_period && c.has_data ? `<span class="chip">${t("screen3.chip.last_period", { period: c.last_period })}</span>` : ""}
        </div>
        ${!c.has_data ? `<p class="callout callout--empty">${t("screen3.no_return", { country: c.name })}</p>` : ""}
        <div class="country-hero__stats">
          ${stat(fmtCount(country.facilities.length), t("screen3.facilities.title"), t("screen3.facilities.active_n", { n: activeFacilities }))}
          ${patientStat("2.6", t("screen1.hero.sentinel"))}
          ${patientStat("2.5", t("screen1.hero.all_conditions"))}
          ${stat(
            String(openQueries.length),
            t("common.open_queries"),
            highSeverity > 0 ? t("screen3.kpi.queries_high", { n: highSeverity }) : "",
          )}
        </div>
      </div>
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

    ${
      country.data_system
        ? `<section class="panel"><div class="panel__header">${panelTitleWithIcon("shield", t("screen4.dsa.title"))}</div><div id="dsa-card"></div></section>`
        : ""
    }
  `;

  // country switcher
  const select = container.querySelector<HTMLSelectElement>("#country-select")!;
  for (const o of [...overview.countries].sort((a, b) => a.name.localeCompare(b.name))) {
    const opt = document.createElement("option");
    opt.value = o.iso3;
    opt.textContent = o.name;
    opt.selected = o.iso3 === iso3;
    select.appendChild(opt);
  }
  select.addEventListener("change", () => navigate({ screen: "country", iso3: select.value }));

  // ---- every indicator, latest period, grouped by Results Framework family
  const groupsHost = container.querySelector("#indicator-groups")!;
  const indicatorValue = (d: IndicatorDim): string => {
    const g = govByIndicatorCode.get(d.indicator_code);
    if (g) return renderStatus(govStatusOf(g), t(statusKey(govStatusOf(g))));
    let v = latestPerIndicator.get(d.indicator_code);
    if ((!v || v.value === null) && latestToDate.has(d.indicator_code))
      v = latestToDate.get(d.indicator_code);
    if (!v || (v.value === null && v.suppressed !== 1)) {
      return `<span class="pill pill--nr">${t("status.not_reported")}</span>`;
    }
    const vt =
      v.disagg_value === "to_date"
        ? t("value_type.to_date")
        : valueTypeLabel(v.value_type, v.as_of, v.indicator_code);
    return `${renderValueWithCompleteness(valueText(v), v.completeness)}
      <small class="indicator-row__meta">${vt ? `${vt} · ` : ""}${v.period_id} ${renderSourceRef(v.source_ref)} ${provenanceOf(v)}</small>`;
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

  // ---- trend: the first preferred indicator with at least two periods
  const seriesFor = (code: string) =>
    country.values
      .filter(
        (v) =>
          v.indicator_code === code &&
          (code === "3.3"
            ? v.disagg_key === "measure" && v.disagg_value === "to_date"
            : v.disagg_key === "all"),
      )
      .sort((a, b) => a.period_id.localeCompare(b.period_id));
  const trendCode = TREND_PREFERENCE.find(
    (code) => seriesFor(code).filter((v) => v.value !== null).length >= 2,
  );
  const dim = trendCode ? dimByCode.get(trendCode) : undefined;
  if (trendCode && dim) {
    const series = seriesFor(trendCode);
    const points: TrendPoint[] = series.map((v) => ({
      period_id: v.period_id,
      value: v.value,
      series: iso3,
      title: `${v.period_id}: ${valueText(v)}${v.source_ref ? ` · ${v.source_ref}` : ""}`,
    }));
    const crossesBreak =
      series.some((v) => v.period_id < PHASE_BREAK_PERIOD) &&
      series.some((v) => v.period_id >= PHASE_BREAK_PERIOD);
    renderChartPanel(container.querySelector("#trend-panel")!, {
      title: `${t("screen3.trend_since")}: ${dim.label_en}`,
      icon: "trend",
      caption: t("screen3.trend.caption"),
      legendHtml: `<span class="chart-legend__item">${t("common.nr_legend")}</span>`,
      buildChart: () =>
        lineTrend(points, {
          valueLabel: dim.label_en,
          seriesBreakAt: crossesBreak ? PHASE_BREAK_PERIOD : undefined,
          seriesBreakLabel: crossesBreak ? t("screen2.trend.break_label") : undefined,
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
            {
              key: "source",
              label: t("common.source_slide"),
              render: (v: GoldRow) => v.source_ref ?? "NR",
            },
          ],
          series,
        ),
      csv: () =>
        tableToCSVData<GoldRow>(
          [
            { key: "period_id", label: "period_id", render: (v) => v.period_id },
            { key: "value", label: "value", render: (v) => (v.value === null ? "NR" : String(v.value)) },
            { key: "source_ref", label: "source_slide", render: (v) => v.source_ref ?? "" },
          ],
          series,
        ),
      csvFilename: `country_${iso3}_${trendCode}_trend`,
    });
  }

  // ---- implementation phase: the published phase, the workbook's steps
  // beside it, a disagreement flagged -- and "no return yet", never "not
  // started", for a country without evidence.
  const stepperHost = container.querySelector("#implementation-stepper")!;
  const stepperPhases = [...new Set(implBundle.steps.map((s) => s.phase_no))].sort((a, b) => a - b);
  const markFor = (s: (typeof implBundle.steps)[number]): string => {
    const row = impl.steps.find((r) => r.step_no === s.step_no);
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
  const disagreement =
    impl.agreement === "no"
      ? `<p class="callout callout--flag">${t("screen_impl.disagreement", {
          workbook: impl.workbook_phase ?? "NR",
          map: impl.icppa_map_phase ?? "NR",
        })}</p>`
      : "";
  stepperHost.innerHTML =
    impl.phase === null
      ? `<p class="callout callout--empty">${t("screen_impl.no_return_country", { country: c.name })}</p>`
      : `<p>${t("screen_impl.column.phase")}: ${phaseChip} <small class="muted">${t("screen_impl.phase_source")}</small></p>
         ${disagreement}
         ${impl.has_steps ? `<div class="implementation-stepper">${stepperMarks}</div>` : ""}`;

  // ---- facilities (curated register: status as a word, partner, the patient figure on the slide)
  const facColumns: Column<FacilityRow>[] = [
    { key: "name", label: t("table.facility"), render: (f) => f.name ?? f.facility_id },
    { key: "district", label: t("table.district"), render: (f) => f.district ?? f.town ?? "NR" },
    { key: "partner", label: t("table.partner"), render: (f) => f.partner ?? "NR" },
    {
      key: "status",
      label: t("table.status"),
      html: true,
      render: (f) => renderRegisterStatus(f),
      csv: (f) => f.register_status ?? "",
    },
    { key: "conditions", label: t("table.conditions"), render: (f) => f.conditions ?? "NR" },
    {
      key: "patients",
      label: t("table.patients_reported"),
      render: (f) => f.patients_reported ?? "NR",
    },
  ];
  const facHost = container.querySelector("#facility-table")!;
  if (country.facilities.length === 0) {
    facHost.innerHTML = `<p class="callout callout--empty">${t("screen3.facilities.none")}</p>`;
  } else {
    facHost.appendChild(
      buildTable(`${c.name}: ${t("screen3.facilities.title")}`, facColumns, country.facilities),
    );
  }

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
  if (country.governance.length === 0) {
    govHost.innerHTML = `<p class="callout callout--empty">${t("empty.no_data")}</p>`;
  } else {
    govHost.appendChild(buildTable(t("screen3.governance.title"), govColumns, country.governance));
  }

  // ---- queries: open first; never "0 open queries" without saying what was tested
  container.querySelector("#queries-list")!.innerHTML =
    country.queries.length === 0
      ? `<p class="callout callout--empty">${t("screen3.queries.none")}</p>`
      : renderQueryList(country.queries);

  const dsaHost = container.querySelector("#dsa-card");
  if (dsaHost && country.data_system) {
    const f = country.data_system.fields;
    dsaHost.innerHTML = `<dl class="definition-panel definition-panel--pair">
      ${Object.entries(f)
        .map(([k, v]) => `<dt>${t(`dsa.${k}`)}</dt><dd>${v}</dd>`)
        .join("")}
    </dl>
    <p class="chart-caption">${t("screen4.dsa.caption", {
      date: fmtDate(country.data_system.assessed_on),
      institution: country.data_system.institution ?? "",
    })}</p>`;
  }
}

/** A facility's register status as a word with a shape (rule 9). */
export function renderRegisterStatus(f: Pick<FacilityRow, "register_status">): string {
  const s = f.register_status ?? "to_confirm";
  return `<span class="reg reg--${s}">${t(`register_status.${s}`)}</span>`;
}
