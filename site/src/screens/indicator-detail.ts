import { getIndicators, getOverview } from "@/lib/bundle";
import { fmtCount, fmtDate, fmtNandN, fmtRateWithNandN, NR } from "@/lib/format";
import { t } from "@/lib/i18n";
import { navigate } from "@/router";
import { renderChartPanel } from "@/components/chart-panel";
import { renderValueWithCompleteness } from "@/components/completeness";
import { renderMilestoneStrip } from "@/components/milestone-strip";
import { panelTitleWithIcon, renderKpiCard, renderKpiRow } from "@/components/kpi";
import { buildTable, tableToCSVData, type Column } from "@/components/table";
import { horizontalBars, type BarDatum } from "@/charts/bar";
import { lineTrend, type TrendPoint } from "@/charts/line";
import type { GoldRow } from "@/lib/types";

const DIRECTION_LABEL: Record<string, string> = {
  increase: "screen2.direction_increase",
  decrease: "screen2.direction_decrease",
  neutral: "screen2.direction_neutral",
};

const PHASE_BREAK_PERIOD = "2026-Q1"; // first Phase Two reporting period, per CLAUDE.md

function latestByCountry(values: GoldRow[]): GoldRow[] {
  const latest = new Map<string, GoldRow>();
  for (const v of values) {
    if (v.disagg_key !== "all") continue;
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

/** A positive gap is a shortfall, a negative gap is over-achievement --
 * `Math.abs` alone erases that sign, so the caption carries the direction
 * and only the magnitude is shown as the number (see components/milestone-strip.ts,
 * where the same fix applies to the strip's own gap text). */
function gapKpiLabel(gap: number | null): string {
  if (gap === null) return t("screen2.kpi.gap");
  if (gap === 0) return t("screen2.kpi.gap_met");
  if (gap < 0) return t("screen2.kpi.gap_exceeded");
  return t("screen2.kpi.gap");
}

export async function renderIndicatorDetail(container: HTMLElement, code: string): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const [bundle, overview] = await Promise.all([getIndicators(), getOverview()]);
  const dim = bundle.dim.find((d) => d.indicator_code === code) ?? bundle.dim[0];
  if (!dim) {
    container.innerHTML = `<p class="callout callout--empty">${t("empty.no_data")}</p>`;
    return;
  }
  const activeDim = dim; // narrowed non-undefined, for use inside closures below
  const values = bundle.values.filter((v) => v.indicator_code === activeDim.indicator_code);
  const valueDisplay =
    dim.regional_value === null
      ? NR
      : dim.unit === "rate"
        ? `${Math.round(dim.regional_value * 100)}%`
        : fmtCount(dim.regional_value);

  container.innerHTML = `
    <h2 class="screen-title">${t("screen2.title")}</h2>
    <p class="panel__question">${t("screen2.question")}</p>

    <div class="screen-controls">
      <label>${t("common.select_indicator")}
        <select id="indicator-select"></select>
      </label>
      <span class="chip" title="${t("screen2.kpi.direction")}">${t(DIRECTION_LABEL[dim.direction ?? "neutral"] ?? "screen2.direction_neutral")}</span>
    </div>

    ${renderKpiRow([
      renderKpiCard("pulse", valueDisplay, t("screen2.kpi.value"), dim.regional_value === null),
      renderKpiCard(
        "target",
        dim.gap === null ? t("common.no_milestone") : fmtCount(Math.abs(dim.gap)),
        gapKpiLabel(dim.gap),
        dim.gap === null,
      ),
      renderKpiCard(
        "country",
        `${dim.countries_reporting} / ${overview.countries.length}`,
        t("screen2.kpi.reporting"),
      ),
    ])}

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("shield", dim.label_en)}</div>
      <dl class="definition-panel">
        <dt>${t("common.definition")}</dt><dd>${dim.definition ?? NR}</dd>
        <dt>${t("common.formula")}</dt><dd>${dim.formula ?? NR}</dd>
      </dl>
      ${renderMilestoneStrip([
        {
          indicator_code: dim.indicator_code,
          label_en: t("common.gap_to_milestone"),
          unit: dim.unit,
          value: dim.regional_value,
          as_of: dim.regional_as_of,
          milestone: dim.milestone,
          gap: dim.gap,
          countries_reporting: dim.countries_reporting,
          countries_total: 0,
        },
      ])}
    </section>

    <div id="distribution-panel"></div>
    <div class="screen-controls" id="trend-controls"></div>
    <div id="trend-panel"></div>
    <p class="chart-caption">${t("screen2.no_league_table")}</p>
  `;

  const select = container.querySelector<HTMLSelectElement>("#indicator-select")!;
  for (const d of bundle.dim) {
    const opt = document.createElement("option");
    opt.value = d.indicator_code;
    opt.textContent = `${d.indicator_code}: ${d.label_en}`;
    opt.selected = d.indicator_code === dim.indicator_code;
    select.appendChild(opt);
  }
  select.addEventListener("change", () => navigate({ screen: "indicator", code: select.value }));

  // ---- distribution: latest period, one bar per reporting country (rule: no league table -> alphabetical)
  // A suppressed row keeps value===null (the real number is withheld) but
  // must stay in the chart as a flagged stub, not disappear as if the
  // country never reported (CLAUDE.md rule 7). A genuine non-response
  // (never suppressed, just never reported) is still dropped.
  const latest = latestByCountry(values).filter((v) => v.value !== null || v.suppressed === 1);
  const barData: BarDatum[] = latest
    .sort((a, b) => a.iso3.localeCompare(b.iso3))
    .map((v) => ({
      label: v.iso3,
      value: v.value,
      suppressed: v.suppressed === 1,
      title: `${v.iso3}: ${valueTitle(v)}`,
    }));

  renderChartPanel(container.querySelector("#distribution-panel")!, {
    title: t("screen2.distribution.title"),
    icon: "grid",
    caption: t("screen2.distribution.caption"),
    legendHtml: `<span class="chart-legend__item"><span class="chart-legend__swatch" style="background:var(--color-accent)"></span>${t("common.suppressed_note", { n: 5 })}</span>`,
    buildChart: () => horizontalBars(barData, { valueLabel: dim.label_en }),
    buildTable: () => {
      const columns: Column<GoldRow>[] = [
        { key: "iso3", label: t("common.select_country"), render: (v) => v.iso3 },
        {
          key: "value",
          label: dim.label_en,
          numeric: true,
          html: true,
          render: (v) => renderValueWithCompleteness(valueTitle(v), v.completeness),
          csv: valueTitle,
        },
        { key: "as_of", label: t("common.as_of"), render: (v) => fmtDate(v.as_of) },
      ];
      return buildTable(`${dim.label_en}: ${t("screen2.distribution.title")}`, columns, latest);
    },
    csv: () =>
      tableToCSVData<GoldRow>(
        [
          { key: "iso3", label: "iso3", render: (v) => v.iso3 },
          {
            key: "numerator",
            label: "numerator",
            render: (v) => (v.numerator === null ? "NR" : String(v.numerator)),
          },
          {
            key: "denominator",
            label: "denominator",
            render: (v) => (v.denominator === null ? "NR" : String(v.denominator)),
          },
          { key: "value", label: "value", render: (v) => (v.value === null ? "NR" : String(v.value)) },
          { key: "as_of", label: "as_of", render: (v) => v.as_of },
        ],
        latest,
      ),
    csvFilename: `indicator_${dim.indicator_code}_distribution`,
  });

  // ---- trend: one country at a time, chosen from a dropdown, to avoid an
  // unreadable 31-line overlay and to avoid summing countries into a
  // regional series the pipeline has not computed (rule: no front-end arithmetic).
  const countriesWithData = [...new Set(values.map((v) => v.iso3))].sort();
  // Default to the country with the most reported periods for this
  // indicator, not the alphabetically first one -- picking a country with a
  // single data point (Angola, alphabetically) made the very first trend
  // chart a viewer sees a lone dot on an otherwise empty axis (design
  // review, boardroom UX pass). The dropdown itself stays alphabetical;
  // only the initial selection changes. A pure count, no arithmetic.
  const nonNullPeriodsByCountry = new Map<string, number>();
  for (const v of values) {
    if (v.disagg_key !== "all" || v.value === null) continue;
    nonNullPeriodsByCountry.set(v.iso3, (nonNullPeriodsByCountry.get(v.iso3) ?? 0) + 1);
  }
  const defaultTrendCountry = [...countriesWithData].sort(
    (a, b) => (nonNullPeriodsByCountry.get(b) ?? 0) - (nonNullPeriodsByCountry.get(a) ?? 0),
  )[0];
  const trendControls = container.querySelector("#trend-controls")!;
  trendControls.innerHTML = `<label>${t("common.select_country")}
    <select id="trend-country-select">${countriesWithData.map((c) => `<option value="${c}" ${c === defaultTrendCountry ? "selected" : ""}>${c}</option>`).join("")}</select>
  </label>`;
  const trendSelect = trendControls.querySelector<HTMLSelectElement>("#trend-country-select")!;

  function renderTrendFor(iso3: string) {
    const series = values
      .filter((v) => v.disagg_key === "all" && v.iso3 === iso3)
      .sort((a, b) => a.period_id.localeCompare(b.period_id));
    const points: TrendPoint[] = series.map((v) => ({
      period_id: v.period_id,
      value: v.value,
      series: iso3,
      title: `${v.period_id}: ${valueTitle(v)}`,
    }));
    const crossesBreak =
      series.some((v) => v.period_id < PHASE_BREAK_PERIOD) &&
      series.some((v) => v.period_id >= PHASE_BREAK_PERIOD);

    renderChartPanel(container.querySelector("#trend-panel")!, {
      title: `${t("screen2.trend.title")}: ${iso3}`,
      icon: "trend",
      caption: t("screen2.trend.caption"),
      legendHtml: `<span class="chart-legend__item">${t("common.nr_legend")}</span>`,
      buildChart: () =>
        lineTrend(points, {
          valueLabel: activeDim.label_en,
          seriesBreakAt: crossesBreak ? PHASE_BREAK_PERIOD : undefined,
          seriesBreakLabel: crossesBreak ? "Phase 1 → 2" : undefined,
        }),
      buildTable: () => {
        const columns: Column<GoldRow>[] = [
          { key: "period_id", label: t("common.select_period"), render: (v) => v.period_id },
          { key: "value", label: activeDim.label_en, numeric: true, render: valueTitle },
          {
            key: "basis",
            label: t("common.historical"),
            render: (v) => (v.basis === "historical" ? t("common.historical") : ""),
          },
        ];
        return buildTable(`${iso3}: ${activeDim.label_en}`, columns, series);
      },
      csv: () =>
        tableToCSVData<GoldRow>(
          [
            { key: "period_id", label: "period_id", render: (v) => v.period_id },
            { key: "value", label: "value", render: (v) => (v.value === null ? "NR" : String(v.value)) },
            { key: "basis", label: "basis", render: (v) => v.basis },
          ],
          series,
        ),
      csvFilename: `indicator_${activeDim.indicator_code}_${iso3}_trend`,
    });
  }
  trendSelect.addEventListener("change", () => renderTrendFor(trendSelect.value));
  if (defaultTrendCountry) renderTrendFor(defaultTrendCountry);
}
