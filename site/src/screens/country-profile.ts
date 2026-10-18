import { getCountry, getImplementation, getIndicators, getOverview } from "@/lib/bundle";
import { fmtCount, fmtRate } from "@/lib/format";
import { t } from "@/lib/i18n";
import { navigate } from "@/router";
import { renderChartPanel } from "@/components/chart-panel";
import { renderStatus, statusFromGovernance, statusFromImplementationStep, statusKey } from "@/lib/status";
import { panelTitleWithIcon } from "@/components/kpi";
import { buildTable, tableToCSVData, type Column } from "@/components/table";
import { renderQueryList } from "@/components/queries";
import { loadWhoGeo, renderCountryMap } from "@/components/facility-map";
import { lineTrend, type TrendPoint } from "@/charts/line";
import { byName, countryName, indicatorLabel } from "@/lib/names";
import { COUNTRY_ASSETS, SHOW_COAT_OF_ARMS } from "@/config";
import type { FacilityRow, GoldRow, GovernanceRow, IndicatorDim } from "@/lib/types";

const PHASE_BREAK_PERIOD = "2026-Q1";
/** The trend shown on the profile: the first of these with a series. */
const TREND_PREFERENCE = ["2.6", "2.6a", "2.5", "3.3"];

function shortValue(v: GoldRow): string {
  return v.unit === "rate" ? fmtRate(v.value) : fmtCount(v.value);
}

/**
 * Screen 3: "What is the position of this country?" A header with the
 * country's outline (WHO boundaries) and its facilities, four key figures,
 * the indicators it reports, its trend, implementation steps, facilities and
 * governance milestones. Data queries sit in a closed "notes" section.
 */
export async function renderCountryProfile(container: HTMLElement, iso3: string): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const [country, indicatorsBundle, implBundle, overview, geo] = await Promise.all([
    getCountry(iso3),
    getIndicators(),
    getImplementation(),
    getOverview(),
    loadWhoGeo(),
  ]);
  const dimByCode = new Map<string, IndicatorDim>(indicatorsBundle.dim.map((d) => [d.indicator_code, d]));
  const c = country.country;
  const name = countryName(c.iso3, c.name);
  const impl = country.implementation;
  const row = overview.country_table.find((r) => r.iso3 === c.iso3);

  // latest value per indicator (all-countries rows), plus 3.3 "to date"
  const latest = new Map<string, GoldRow>();
  for (const v of country.values) {
    const isToDate = v.indicator_code === "3.3" && v.disagg_key === "measure" && v.disagg_value === "to_date";
    if (v.disagg_key !== "all" && !isToDate) continue;
    if (v.indicator_code === "3.3" && !isToDate) continue;
    const prev = latest.get(v.indicator_code);
    if (!prev || v.period_id > prev.period_id) latest.set(v.indicator_code, v);
  }
  const govByCode = new Map(country.governance.map((g) => [g.milestone_code, g]));
  const govStatusOf = (g: GovernanceRow) => statusFromGovernance(g.status, Boolean(g.document));

  const reported = indicatorsBundle.dim.filter((d) => {
    const v = latest.get(d.indicator_code);
    return (v && v.value !== null) || govByCode.has(d.indicator_code);
  });
  const missing = indicatorsBundle.dim.filter((d) => !reported.includes(d));

  const assets = COUNTRY_ASSETS[c.iso3] ?? {};
  const armsHtml =
    SHOW_COAT_OF_ARMS && assets.arms
      ? `<img class="cprofile__arms" src="${import.meta.env.BASE_URL}assets/countries/${c.iso3}/${assets.arms}" alt="${t("screen3.arms_alt", { country: name })}" />`
      : "";
  const phaseChip =
    impl.phase !== null
      ? `<span class="cprofile__chip">${t("screen_impl.phase_n", { n: impl.phase })} · ${t(`screen3.phase_name.${impl.phase}`)}</span>`
      : `<span class="cprofile__chip is-muted">${t("screen1.table.no_data")}</span>`;
  const big = (value: string, label: string, sub = "") =>
    `<div class="cprofile__fig"><b class="num">${value}</b><span>${label}</span>${sub ? `<small>${sub}</small>` : ""}</div>`;
  const patients =
    row?.patients !== null && row?.patients !== undefined
      ? big(
          fmtCount(row.patients),
          t("screen1.kpi.patients"),
          row.patients_held ? t("screen1.table.to_check") : t("screen3.fig.sentinel"),
        )
      : row?.patients_all !== null && row?.patients_all !== undefined
        ? big(fmtCount(row.patients_all), t("screen1.kpi.patients"), t("screen1.table.all_conditions"))
        : row?.patients_active !== null && row?.patients_active !== undefined
          ? big(fmtCount(row.patients_active), t("screen1.kpi.patients"), t("screen1.table.in_care"))
          : big("—", t("screen1.kpi.patients"));

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

    <section class="cprofile">
      <div class="cprofile__map" id="country-map"></div>
      <div class="cprofile__body">
        <div class="cprofile__titlerow">
          <div>
            <span class="cprofile__eyebrow">${t(c.cohort === "phase_1" ? "common.phase1" : "common.phase2")}</span>
            <h1>${name}</h1>
          </div>
          ${armsHtml}
        </div>
        <div class="cprofile__chips">${phaseChip}${
          row?.latest_period
            ? `<span class="cprofile__chip is-ghost">${t("screen3.chip.latest", { period: row.latest_period.replace("-A", "") })}</span>`
            : ""
        }</div>
        ${!c.has_data ? `<p class="cprofile__empty">${t("screen3.no_return", { country: name })}</p>` : ""}
        <div class="cprofile__figs">
          ${big(row?.facilities !== null && row?.facilities !== undefined ? fmtCount(row.facilities) : "—", t("screen1.kpi.facilities"), t("screen3.fig.facilities_named", { n: country.facilities.length }))}
          ${patients}
          ${big(row?.trained !== null && row?.trained !== undefined ? fmtCount(row.trained) : "—", t("screen1.kpi.trained"), t("screen1.kpi.trained_sub"))}
          ${big(impl.phase !== null ? String(impl.phase) : "—", t("screen3.fig.phase"), t("screen3.fig.phase_sub"))}
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("grid", t("screen3.indicators.title"))}</div>
      <div class="ind-tiles" id="ind-tiles"></div>
      ${
        missing.length
          ? `<p class="ind-missing"><span>${t("screen3.indicators.missing")}</span> ${missing
              .map(
                (d) =>
                  `<abbr title="${indicatorLabel(d.indicator_code, d.label_en).replace(/"/g, "&quot;")}">${d.indicator_code}</abbr>`,
              )
              .join(" ")}</p>`
          : ""
      }
    </section>

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

    <details class="panel notes">
      <summary>${panelTitleWithIcon("alert", t("screen3.notes.title", { n: country.queries.filter((q) => q.status === "open").length }))}</summary>
      <div id="queries-list"></div>
    </details>
  `;

  // header map: the country's WHO outline with its facilities
  const map = renderCountryMap(geo, c.iso3, country.facilities);
  if (map) container.querySelector("#country-map")!.appendChild(map);

  // country switcher, alphabetical in the reader's language
  const select = container.querySelector<HTMLSelectElement>("#country-select")!;
  for (const o of [...overview.countries].sort((a, b) =>
    byName(countryName(a.iso3, a.name), countryName(b.iso3, b.name)),
  )) {
    const opt = document.createElement("option");
    opt.value = o.iso3;
    opt.textContent = countryName(o.iso3, o.name);
    opt.selected = o.iso3 === iso3;
    select.appendChild(opt);
  }
  select.addEventListener("change", () => navigate({ screen: "country", iso3: select.value }));

  // indicators the country reports: one tile each
  container.querySelector("#ind-tiles")!.innerHTML = reported.length
    ? reported
        .map((d) => {
          const g = govByCode.get(d.indicator_code);
          const v = latest.get(d.indicator_code);
          const value = g
            ? renderStatus(govStatusOf(g), t(statusKey(govStatusOf(g))))
            : `<b class="num">${shortValue(v!)}</b>`;
          const meta = g ? (g.achieved_in ?? "") : v!.period_id.replace("-A", "");
          return `<button type="button" class="ind-tile${v?.held ? " is-held" : ""}" data-code="${d.indicator_code}">
            <span class="ind-tile__code">${d.indicator_code}</span>
            <span class="ind-tile__label">${indicatorLabel(d.indicator_code, d.label_en)}</span>
            <span class="ind-tile__value">${value}</span>
            <span class="ind-tile__meta">${v?.held ? `<span class="tag-check">${t("screen1.table.to_check")}</span>` : meta}</span>
          </button>`;
        })
        .join("")
    : `<p class="cprofile__empty">${t("screen3.indicators.none")}</p>`;
  container
    .querySelectorAll<HTMLButtonElement>(".ind-tile")
    .forEach((b) =>
      b.addEventListener("click", () => navigate({ screen: "indicator", code: b.dataset.code! })),
    );

  // trend: the first preferred indicator with at least two periods
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
    const label = indicatorLabel(dim.indicator_code, dim.label_en);
    const series = seriesFor(trendCode);
    const points: TrendPoint[] = series.map((v) => ({
      period_id: v.period_id,
      value: v.value,
      series: iso3,
      title: `${v.period_id.replace("-A", "")}: ${shortValue(v)}`,
    }));
    const crossesBreak =
      series.some((v) => v.period_id < PHASE_BREAK_PERIOD) &&
      series.some((v) => v.period_id >= PHASE_BREAK_PERIOD);
    renderChartPanel(container.querySelector("#trend-panel")!, {
      title: `${t("screen3.trend.title")} · ${label}`,
      icon: "trend",
      caption: t("screen3.trend.caption"),
      buildChart: () =>
        lineTrend(points, {
          valueLabel: label,
          seriesBreakAt: crossesBreak ? PHASE_BREAK_PERIOD : undefined,
          seriesBreakLabel: crossesBreak ? t("screen2.trend.break_label") : undefined,
          height: 280,
        }),
      buildTable: () =>
        buildTable(
          label,
          [
            {
              key: "period",
              label: t("table.latest_period"),
              render: (v: GoldRow) => v.period_id.replace("-A", ""),
            },
            { key: "value", label, numeric: true, render: (v: GoldRow) => shortValue(v) },
          ],
          series,
        ),
      csv: () =>
        tableToCSVData<GoldRow>(
          [
            { key: "period", label: "period", render: (v) => v.period_id },
            { key: "value", label: "value", render: (v) => (v.value === null ? "NR" : String(v.value)) },
          ],
          series,
        ),
      csvFilename: `country_${iso3}_${trendCode}_trend`,
    });
  }

  // implementation: fourteen steps grouped by phase
  const stepperHost = container.querySelector("#implementation-stepper")!;
  const phases = [...new Set(implBundle.steps.map((s) => s.phase_no))].sort((a, b) => a - b);
  const markFor = (s: (typeof implBundle.steps)[number]): string => {
    const r = impl.steps.find((x) => x.step_no === s.step_no);
    const status = statusFromImplementationStep(r?.status ?? null);
    const title = `${s.step_no}. ${s.step_label} · ${t(statusKey(status))}`.replace(/"/g, "&quot;");
    return `<span class="implementation-stepper__mark" title="${title}">${renderStatus(status, String(s.step_no))}</span>`;
  };
  stepperHost.innerHTML =
    impl.phase === null
      ? `<p class="cprofile__empty">${t("screen_impl.no_return_country", { country: name })}</p>`
      : `<p class="impl-line">${t("screen3.impl.line", { n: impl.phase, name: t(`screen3.phase_name.${impl.phase}`) })}${
          impl.agreement === "no"
            ? ` <span class="impl-note">${t("screen3.impl.workbook", { n: impl.workbook_phase ?? "—" })}</span>`
            : ""
        }</p>
        ${
          impl.has_steps
            ? `<div class="implementation-stepper">${phases
                .map(
                  (
                    n,
                  ) => `<div class="stepper-phase${impl.phase !== null && n <= impl.phase ? " is-reached" : ""}">
                  <div class="stepper-phase__marks">${implBundle.steps
                    .filter((s) => s.phase_no === n)
                    .map(markFor)
                    .join("")}</div>
                  <small>${t("screen_impl.phase_n", { n })}</small></div>`,
                )
                .join("")}</div>`
            : ""
        }`;

  // facilities
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
  ];
  const facHost = container.querySelector("#facility-table")!;
  if (country.facilities.length === 0) {
    facHost.innerHTML = `<p class="cprofile__empty">${t("screen3.facilities.none")}</p>`;
  } else {
    facHost.appendChild(
      buildTable(`${name}: ${t("screen3.facilities.title")}`, facColumns, country.facilities),
    );
  }

  // governance milestones: "a Yes without a document title is not counted"
  const govColumns: Column<GovernanceRow>[] = [
    { key: "milestone", label: t("table.milestone"), render: (g) => g.milestone },
    {
      key: "status",
      label: t("table.status"),
      html: true,
      render: (g) => renderStatus(govStatusOf(g), t(statusKey(govStatusOf(g)))),
      csv: (g) => t(statusKey(govStatusOf(g))),
    },
    { key: "document", label: t("table.document"), render: (g) => g.document ?? "NR" },
  ];
  const govHost = container.querySelector("#governance-table")!;
  if (country.governance.length === 0) {
    govHost.innerHTML = `<p class="cprofile__empty">${t("screen3.governance.none")}</p>`;
  } else {
    govHost.appendChild(buildTable(t("screen3.governance.title"), govColumns, country.governance));
  }

  // data notes (queries), closed by default
  container.querySelector("#queries-list")!.innerHTML =
    country.queries.length === 0
      ? `<p class="cprofile__empty">${t("screen3.queries.none_v2")}</p>`
      : renderQueryList(country.queries);
}

/** A facility's register status as a word with a shape (rule 9). */
export function renderRegisterStatus(f: Pick<FacilityRow, "register_status">): string {
  const s = f.register_status ?? "to_confirm";
  return `<span class="reg reg--${s}">${t(`register_status.${s}`)}</span>`;
}
