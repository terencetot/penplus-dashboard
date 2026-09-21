import { getCountry, getIndicators, getOverview } from "@/lib/bundle";
import { fmtCount, fmtDate, fmtRateWithNandN } from "@/lib/format";
import { t } from "@/lib/i18n";
import { navigate } from "@/router";
import { renderChartPanel } from "@/components/chart-panel";
import { renderStatus, statusFromGovernance, statusKey } from "@/lib/status";
import { facilityStatusKey, projectSupportedKey } from "@/lib/vocab";
import { buildTable, tableToCSVData, type Column } from "@/components/table";
import { lineTrend, type TrendPoint } from "@/charts/line";
import type { GoldRow, GovernanceRow, IndicatorDim, OpenQuery } from "@/lib/types";

const PHASE_BREAK_PERIOD = "2026-Q1";

function valueText(v: GoldRow): string {
  return v.unit === "rate" ? fmtRateWithNandN(v.numerator, v.denominator, v.value) : fmtCount(v.value);
}

export async function renderCountryProfile(container: HTMLElement, iso3: string): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const [country, indicatorsBundle] = await Promise.all([getCountry(iso3), getIndicators()]);
  const dimByCode = new Map<string, IndicatorDim>(indicatorsBundle.dim.map((d) => [d.indicator_code, d]));

  container.innerHTML = `
    <h2 class="screen-title">${t("screen3.title")} — ${country.country.name}</h2>
    <p class="panel__question">${t("screen3.question")}</p>

    <div class="screen-controls">
      <label>${t("common.select_country")}
        <select id="country-select"></select>
      </label>
      <span class="chip">${country.country.cohort === "phase_1" ? t("common.phase1") : t("common.phase2")}</span>
    </div>

    ${country.country.returns === 0 ? `<p class="callout callout--empty">${t("screen3.no_return", { country: country.country.name })}</p>` : ""}

    <section class="panel">
      <div class="panel__header"><h3 class="panel__title">${t("screen3.all_indicators")}</h3></div>
      <div id="indicator-table"></div>
    </section>

    <div id="trend-panel"></div>

    <section class="panel">
      <div class="panel__header"><h3 class="panel__title">${t("screen3.facilities.title")}</h3></div>
      <div id="facility-table"></div>
    </section>

    <section class="panel">
      <div class="panel__header"><h3 class="panel__title">${t("screen3.governance.title")}</h3></div>
      <div id="governance-table"></div>
    </section>

    <section class="panel">
      <div class="panel__header"><h3 class="panel__title">${t("screen3.queries.title")}</h3></div>
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

  // ---- all sixteen indicators for this country, latest period each (acceptance criterion 3)
  const latestPerIndicator = new Map<string, GoldRow>();
  for (const v of country.values) {
    if (v.disagg_key !== "all") continue;
    const prev = latestPerIndicator.get(v.indicator_code);
    if (!prev || v.period_id > prev.period_id) latestPerIndicator.set(v.indicator_code, v);
  }
  const indicatorColumns: Column<IndicatorDim>[] = [
    { key: "code", label: "#", render: (d) => d.indicator_code },
    { key: "label", label: t("common.select_indicator"), render: (d) => d.label_en },
    {
      key: "value",
      label: t("table.value"),
      numeric: true,
      render: (d) => {
        const v = latestPerIndicator.get(d.indicator_code);
        return v ? valueText(v) : "NR";
      },
    },
    {
      key: "as_of",
      label: t("common.as_of"),
      render: (d) => {
        const v = latestPerIndicator.get(d.indicator_code);
        return v ? fmtDate(v.as_of) : "NR";
      },
    },
  ];
  container
    .querySelector("#indicator-table")!
    .appendChild(
      buildTable(
        `${country.country.name} — ${t("screen3.all_indicators")}`,
        indicatorColumns,
        indicatorsBundle.dim,
      ),
    );

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
      title: `${t("screen3.trend_since")} — ${dim.label_en}`,
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
            { key: "value", label: dim.label_en, numeric: true, render: valueText },
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

  // ---- facilities
  const facColumns: Column<(typeof country.facilities)[number]>[] = [
    { key: "name", label: t("table.facility"), render: (f) => f.name },
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
      buildTable(
        `${country.country.name} — ${t("screen3.facilities.title")}`,
        facColumns,
        country.facilities,
      ),
    );

  // ---- governance milestones: "a Yes without a document title is not counted"
  const govStatusOf = (g: GovernanceRow) => statusFromGovernance(g.status, Boolean(g.document));
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
        <strong>${q.severity}</strong> — ${q.period_id} — ${q.section} / ${q.field}<br>
        ${q.question}
      </div>`,
      )
      .join("");
  }
}
