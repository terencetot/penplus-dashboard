import * as Plot from "@observablehq/plot";
import { getIndicators, getOverview } from "@/lib/bundle";
import { fmtCount, fmtDate, fmtNandN, fmtRate, fmtRateWithNandN, NR } from "@/lib/format";
import { t } from "@/lib/i18n";
import { navigate } from "@/router";
import { renderChartPanel } from "@/components/chart-panel";
import { renderValueWithCompleteness } from "@/components/completeness";
import { coverageTile, statTile } from "@/components/stat";
import { lineTrend, type TrendPoint } from "@/charts/line";
import { horizontalBars, type BarDatum } from "@/charts/bar";
import { buildTable, tableToCSVData, type Column } from "@/components/table";
import { byName, countryName, indicatorDefinition, indicatorLabel } from "@/lib/names";
import type { GoldRow } from "@/lib/types";

const PHASE_BREAK_PERIOD = "2026-Q1"; // first Phase Two reporting period, per CLAUDE.md
/** A trend line only where a real series exists: three or more reported periods. */
const MIN_TREND_PERIODS = 3;
/** Sentinel conditions, in the design brief's colours (charts only, never performance). */
const CONDITIONS: { key: string; colour: string }[] = [
  { key: "t1d", colour: "#016294" },
  { key: "scd", colour: "#c8102e" },
  { key: "rhd", colour: "#6b4fa0" },
  { key: "cardiac_not_split", colour: "#8792a8" },
  { key: "sentinel_not_split", colour: "#b6bfcf" },
];

function latestByCountry(values: GoldRow[], key = "all", val = "all"): GoldRow[] {
  const latest = new Map<string, GoldRow>();
  for (const v of values) {
    if (v.disagg_key !== key || v.disagg_value !== val) continue;
    const prev = latest.get(v.iso3);
    if (!prev || v.period_id > prev.period_id) latest.set(v.iso3, v);
  }
  return [...latest.values()];
}

function valueTitle(v: GoldRow): string {
  if (v.suppressed === 1) return t("common.suppressed");
  return v.unit === "rate"
    ? fmtRateWithNandN(v.numerator, v.denominator, v.value)
    : `${fmtCount(v.value)} (${fmtNandN(v.numerator, v.denominator)})`;
}

/**
 * Screen 2: "Is this indicator moving, and which countries drive it?" Three
 * figure tiles, the definition, the comparison across countries (always
 * alphabetical), the split by condition for the sentinel cohort, and trends
 * where a country has a real series.
 */
export async function renderIndicatorDetail(container: HTMLElement, code: string): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const [bundle, overview] = await Promise.all([getIndicators(), getOverview()]);
  const dim = bundle.dim.find((d) => d.indicator_code === code) ?? bundle.dim[0];
  if (!dim) {
    container.innerHTML = `<p class="callout callout--empty">${t("empty.no_data")}</p>`;
    return;
  }
  const activeDim = dim;
  const values = bundle.values.filter((v) => v.indicator_code === activeDim.indicator_code);
  const nameOf = (iso3: string) =>
    countryName(iso3, overview.countries.find((c) => c.iso3 === iso3)?.name ?? iso3);
  const label = indicatorLabel(dim.indicator_code, dim.label_en);

  const regional =
    dim.regional_value === null
      ? "—"
      : dim.unit === "rate"
        ? fmtRate(dim.regional_value)
        : fmtCount(dim.regional_value);

  container.innerHTML = `
    <header class="page-head">
      <h2 class="screen-title">${t("screen2.title")}</h2>
      <p class="panel__question">${t("screen2.question")}</p>
    </header>

    <div class="screen-controls">
      <label>${t("common.select_indicator")}
        <select id="indicator-select"></select>
      </label>
    </div>

    <div class="stat-row stat-row--3">
      ${coverageTile(t("screen2.kpi.value"), regional, label, dim)}
      ${statTile(
        t("screen2.kpi.updated"),
        dim.regional_as_of ? fmtDate(dim.regional_as_of) : "—",
        t("screen2.kpi.updated_sub"),
        "stat--date",
      )}
      ${statTile(
        t("screen2.kpi.with_value"),
        `${dim.countries_reporting}<small>/${dim.countries_total}</small>`,
        t("screen2.kpi.without_value", { n: dim.countries_without }),
      )}
    </div>

    <section class="panel definition">
      <span class="definition__code">${dim.indicator_code}</span>
      <div>
        <h3 class="panel__title">${label}</h3>
        <p>${indicatorDefinition(dim.indicator_code, dim.definition) ?? NR}</p>
      </div>
    </section>

    <div id="distribution-panel"></div>
    <div id="condition-panel"></div>
    <div id="trend-panel"></div>
  `;

  // ---- indicator picker: indicators with data first
  const select = container.querySelector<HTMLSelectElement>("#indicator-select")!;
  const withData = bundle.dim.filter((d) => d.countries_reporting > 0);
  const noData = bundle.dim.filter((d) => d.countries_reporting === 0);
  const group = (label: string, dims: typeof bundle.dim) => {
    const og = document.createElement("optgroup");
    og.label = label;
    for (const d of dims) {
      const opt = document.createElement("option");
      opt.value = d.indicator_code;
      opt.textContent = `${d.indicator_code} · ${indicatorLabel(d.indicator_code, d.label_en)}`;
      opt.selected = d.indicator_code === dim.indicator_code;
      og.appendChild(opt);
    }
    select.appendChild(og);
  };
  group(t("screen2.picker.with_data"), withData);
  if (noData.length) group(t("screen2.picker.no_data"), noData);
  select.addEventListener("change", () => navigate({ screen: "indicator", code: select.value }));

  // ---- comparison across countries: latest value, alphabetical (rule 5)
  const reporting = latestByCountry(values).filter((v) => v.value !== null || v.suppressed === 1);
  const notReporting = overview.countries
    .filter((c) => !reporting.some((v) => v.iso3 === c.iso3))
    .sort((a, b) => byName(nameOf(a.iso3), nameOf(b.iso3)));
  const heldLabel = t("prov.held");
  const barData: BarDatum[] = reporting
    .sort((a, b) => byName(nameOf(a.iso3), nameOf(b.iso3)))
    .map((v) => ({
      label: nameOf(v.iso3),
      value: v.value,
      suppressed: v.suppressed === 1,
      held: v.held === 1,
      title: `${nameOf(v.iso3)}: ${valueTitle(v)}${v.held ? ` · ${heldLabel}` : ""}`,
    }));

  renderChartPanel(container.querySelector("#distribution-panel")!, {
    title: t("screen2.distribution.title"),
    icon: "grid",
    caption: t("screen2.distribution.caption_v2"),
    buildChart: () => {
      const wrap = document.createElement("div");
      wrap.appendChild(horizontalBars(barData, { valueLabel: label, heldLabel }));
      if (notReporting.length > 0) {
        const more = document.createElement("details");
        more.className = "not-reporting";
        more.innerHTML = `<summary>${t("screen2.distribution.no_value", { n: notReporting.length })}</summary>
          <p>${notReporting.map((c) => nameOf(c.iso3)).join(" · ")}</p>`;
        wrap.appendChild(more);
      }
      return wrap;
    },
    buildTable: () => {
      const columns: Column<GoldRow>[] = [
        { key: "iso3", label: t("common.select_country"), render: (v) => nameOf(v.iso3) },
        {
          key: "value",
          label: label,
          numeric: true,
          html: true,
          render: (v) => renderValueWithCompleteness(valueTitle(v), v.completeness),
          csv: valueTitle,
        },
        { key: "period", label: t("table.latest_period"), render: (v) => v.period_id },
      ];
      return buildTable(`${label}: ${t("screen2.distribution.title")}`, columns, reporting);
    },
    csv: () =>
      tableToCSVData<GoldRow>(
        [
          { key: "iso3", label: "iso3", render: (v) => v.iso3 },
          { key: "country", label: "country", render: (v) => nameOf(v.iso3) },
          { key: "value", label: "value", render: (v) => (v.value === null ? "NR" : String(v.value)) },
          { key: "period", label: "period", render: (v) => v.period_id },
          { key: "as_of", label: "as_of", render: (v) => v.as_of },
          { key: "to_verify", label: "to_verify", render: (v) => (v.held ? "yes" : "") },
        ],
        reporting,
      ),
    csvFilename: `indicator_${dim.indicator_code}_by_country`,
  });

  // ---- sentinel cohort by condition (2.6 and 2.6a): stacked parts of each
  // country's own total, with a legend in words (rule 9)
  const conditionHost = container.querySelector<HTMLElement>("#condition-panel")!;
  if (dim.indicator_code === "2.6" || dim.indicator_code === "2.6a") {
    const parts = CONDITIONS.flatMap(({ key }) =>
      latestByCountry(values, "condition", key)
        .filter((v) => v.value !== null && !v.held)
        .map((v) => ({ country: nameOf(v.iso3), condition: key, value: v.value as number })),
    );
    if (parts.length > 0) {
      const present = CONDITIONS.filter((c) => parts.some((p) => p.condition === c.key));
      const countries = [...new Set(parts.map((p) => p.country))].sort(byName);
      renderChartPanel(conditionHost, {
        title: t("screen2.condition.title"),
        icon: "grid",
        caption: t("screen2.condition.caption"),
        legendHtml: present
          .map(
            (c) =>
              `<span class="chart-legend__item"><span class="chart-legend__swatch" style="background:${c.colour}"></span>${t(`condition.${c.key}`)}</span>`,
          )
          .join(""),
        buildChart: () =>
          Plot.plot({
            width: 1100,
            height: Math.max(160, countries.length * 38 + 40),
            marginLeft: 230,
            marginRight: 24,
            x: { label: null, grid: true, nice: true, tickFormat: (d: number) => fmtCount(d) },
            y: { label: null, domain: countries, padding: 0.35 },
            color: { domain: present.map((c) => c.key), range: present.map((c) => c.colour) },
            style: { fontFamily: "var(--font-family)", fontSize: "13px" },
            marks: [
              Plot.barX(parts, {
                y: "country",
                x: "value",
                fill: "condition",
                rx: 3,
                tip: true,
                title: (d: { country: string; condition: string; value: number }) =>
                  `${d.country} · ${t(`condition.${d.condition}`)}: ${fmtCount(d.value)}`,
              }),
              Plot.ruleX([0]),
            ],
          }),
        buildTable: () =>
          buildTable(
            t("screen2.condition.title"),
            [
              { key: "country", label: t("common.select_country"), render: (d) => d.country },
              {
                key: "condition",
                label: t("table.conditions"),
                render: (d) => t(`condition.${d.condition}`),
              },
              { key: "value", label: label, numeric: true, render: (d) => fmtCount(d.value) },
            ],
            parts,
          ),
        csv: () => ({
          headers: ["country", "condition", "value"],
          rows: parts.map((d) => [d.country, d.condition, String(d.value)]),
        }),
        csvFilename: `indicator_${dim.indicator_code}_by_condition`,
      });
    }
  }

  // ---- trends: every country with a real series, alphabetical
  const periodsByCountry = new Map<string, number>();
  for (const v of values) {
    if (v.disagg_key !== "all" || v.value === null) continue;
    periodsByCountry.set(v.iso3, (periodsByCountry.get(v.iso3) ?? 0) + 1);
  }
  const trendCountries = [...periodsByCountry.keys()]
    .filter((iso3) => (periodsByCountry.get(iso3) ?? 0) >= MIN_TREND_PERIODS)
    .sort((a, b) => byName(nameOf(a), nameOf(b)));
  const trendHost = container.querySelector("#trend-panel")!;
  if (trendCountries.length > 0) {
    const panel = document.createElement("section");
    panel.className = "panel";
    panel.innerHTML = `<h3 class="panel__title">${t("screen2.trend.title")}</h3>
      <p class="panel__question">${t("screen2.trend.caption")}</p>
      <div class="trend-grid"></div>`;
    const grid = panel.querySelector(".trend-grid")!;
    for (const iso3 of trendCountries) {
      const series = values
        .filter((v) => v.disagg_key === "all" && v.iso3 === iso3)
        .sort((a, b) => a.period_id.localeCompare(b.period_id));
      const latest = series[series.length - 1];
      const points: TrendPoint[] = series.map((v) => ({
        period_id: v.period_id,
        value: v.value,
        series: iso3,
        title: `${v.period_id}: ${valueTitle(v)}`,
      }));
      const crossesBreak =
        series.some((v) => v.period_id < PHASE_BREAK_PERIOD) &&
        series.some((v) => v.period_id >= PHASE_BREAK_PERIOD);
      const card = document.createElement("div");
      card.className = "trend-card";
      card.innerHTML = `<div class="trend-card__head"><span class="trend-card__name">${nameOf(iso3)}</span></div>
        <div class="trend-card__value num">${latest ? fmtCount(latest.value) : NR}<small>${latest?.period_id.replace("-A", "") ?? ""}</small></div>
        <div class="trend-card__chart"></div>`;
      card.querySelector(".trend-card__chart")!.appendChild(
        lineTrend(points, {
          valueLabel: label,
          seriesBreakAt: crossesBreak ? PHASE_BREAK_PERIOD : undefined,
          seriesBreakLabel: crossesBreak ? t("screen2.trend.break_label") : undefined,
          height: 200,
          compact: true,
        }),
      );
      grid.appendChild(card);
    }
    trendHost.replaceChildren(panel);
  }
}
