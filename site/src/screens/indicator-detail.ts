import { getIndicators, getOverview } from "@/lib/bundle";
import { fmtCount, fmtDate, fmtNandN, fmtRateWithNandN, NR } from "@/lib/format";
import { t } from "@/lib/i18n";
import { navigate } from "@/router";
import { renderChartPanel } from "@/components/chart-panel";
import { renderValueWithCompleteness } from "@/components/completeness";
import { renderCoverageCard } from "@/components/coverage-card";
import { lineTrend, type TrendPoint } from "@/charts/line";
import { horizontalBars, type BarDatum } from "@/charts/bar";
import { buildTable, tableToCSVData, type Column } from "@/components/table";
import { provenanceOf, renderSourceRef, valueTypeLabel } from "@/components/provenance";
import type { GoldRow } from "@/lib/types";

const DIRECTION_LABEL: Record<string, string> = {
  increase: "screen2.direction_increase",
  decrease: "screen2.direction_decrease",
  neutral: "screen2.direction_neutral",
};

const PHASE_BREAK_PERIOD = "2026-Q1"; // first Phase Two reporting period, per CLAUDE.md
/** A trend line is drawn only where a real series exists: three or more
 * published periods for the country (audit v2: Sierra Leone, Uganda,
 * Liberia, Kenya; Rwanda as active). Two points are not a trend. */
const MIN_TREND_PERIODS = 3;

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

  // ---- KPI row: card 1 is the richer coverage card (pips + partial badge,
  // same component as the overview hero); cards 2 and 3 are simpler single
  // figures, built here since neither carries a coverage share of its own.
  const gapHasValue = dim.gap !== null;
  const gapText = gapHasValue ? fmtCount(Math.abs(dim.gap!)) : t("common.no_milestone");
  const withoutValue = dim.countries_total - dim.countries_reporting;
  const regionalValueDisplay =
    dim.regional_value === null
      ? undefined
      : dim.unit === "rate"
        ? `${Math.round(dim.regional_value * 100)}%`
        : undefined; // fmtCount's default formatting is already right for a count

  container.innerHTML = `
    <header class="page-head">
      <h2 class="screen-title">${t("screen2.title")}</h2>
      <p class="panel__question">${t("screen2.question")}</p>
    </header>

    <div class="screen-controls">
      <label>${t("common.select_indicator")}
        <select id="indicator-select"></select>
      </label>
      <span class="chip" title="${t("screen2.kpi.direction")}">${t(DIRECTION_LABEL[dim.direction ?? "neutral"] ?? "screen2.direction_neutral")}</span>
      ${
        values.length > 0 && values.every((v) => v.basis === "historical")
          ? `<span class="chip chip--warm" style="margin-left:auto">${t("screen3.chip.historical_evidence")}</span>`
          : ""
      }
    </div>

    <div class="coverage-row">
      ${renderCoverageCard(
        t("screen2.kpi.value"),
        {
          total: dim.regional_value,
          countries_reporting: dim.countries_reporting,
          countries_total: dim.countries_total,
          coverage_pct: dim.coverage_pct,
          total_held_by: dim.regional_held_by,
          countries_held: dim.countries_held,
        },
        dim.regional_as_of,
        regionalValueDisplay,
        dim.value_types.map((vt) => valueTypeLabel(vt)).join(" · ") || undefined,
      )}
      <div class="coverage-card">
        <div class="coverage-card__label">${gapKpiLabel(dim.gap)}</div>
        <div class="coverage-card__value" style="color:var(--color-accent);font-size:${gapHasValue ? "2.6rem" : "1.5rem"}">${gapText}</div>
        <div class="coverage-card__cov">${gapHasValue ? "" : t("screen2.milestone.shown_once")}</div>
      </div>
      <div class="coverage-card">
        <div class="coverage-card__label">${t("screen2.kpi.with_value")}</div>
        <div class="coverage-card__value num">${dim.countries_reporting}<small style="font-family:var(--font-family);font-size:1.1rem;font-weight:500;color:var(--color-text-muted)">/${dim.countries_total}</small></div>
        <div class="coverage-card__cov">${t("screen2.kpi.without_value", { n: withoutValue })}</div>
      </div>
    </div>

    <section class="panel">
      <h3 class="panel__title">${dim.label_en}</h3>
      <dl class="definition-panel definition-panel--pair">
        <dt>${t("common.definition")}</dt><dd>${dim.definition ?? NR}</dd>
        <dt>${t("common.formula")}</dt><dd>${dim.formula ?? NR}</dd>
      </dl>
    </section>

    <div id="distribution-panel"></div>
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
  // (never suppressed, just never reported) is dropped from the bars and
  // listed as a pill instead -- present, never drawn as a zero.
  const allLatest = latestByCountry(values);
  const reporting = allLatest.filter((v) => v.value !== null || v.suppressed === 1);
  const heldLabel = t("prov.held");
  const notReporting = overview.countries
    .filter((c) => !reporting.some((v) => v.iso3 === c.iso3))
    .sort((a, b) => a.name.localeCompare(b.name));
  const nameOf = (iso3: string) => overview.countries.find((c) => c.iso3 === iso3)?.name ?? iso3;
  const barData: BarDatum[] = reporting
    .sort((a, b) => nameOf(a.iso3).localeCompare(nameOf(b.iso3)))
    .map((v) => ({
      label: nameOf(v.iso3),
      value: v.value,
      suppressed: v.suppressed === 1,
      held: v.held === 1,
      title: `${nameOf(v.iso3)}: ${valueTitle(v)}${v.held ? ` · ${heldLabel} (${v.held_by})` : ""}${v.source_ref ? ` · ${v.source_ref}` : ""}`,
    }));

  renderChartPanel(container.querySelector("#distribution-panel")!, {
    title: t("screen2.distribution.title"),
    icon: "grid",
    caption: t("screen2.distribution.caption"),
    legendHtml: `<span class="chart-legend__item"><span class="chart-legend__swatch" style="background:var(--color-accent)"></span>${t("common.suppressed_note", { n: 5 })}</span>
      <span class="chart-legend__item"><span class="chart-legend__swatch chart-legend__swatch--held"></span>${t("screen2.distribution.held_note")}</span>`,
    buildChart: () => {
      const wrap = document.createElement("div");
      wrap.appendChild(horizontalBars(barData, { valueLabel: dim.label_en, heldLabel }));
      if (notReporting.length > 0) {
        const pills = document.createElement("div");
        pills.className = "pill-list";
        pills.innerHTML = notReporting.map((c) => `<span class="pill">${c.name}</span>`).join("");
        wrap.appendChild(pills);
      }
      const note = document.createElement("p");
      note.className = "chart-caption";
      note.textContent = t("screen2.distribution.not_reporting");
      wrap.appendChild(note);
      return wrap;
    },
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
        {
          key: "value_type",
          label: t("common.value_type"),
          render: (v) => valueTypeLabel(v.value_type, v.as_of) || "NR",
        },
        { key: "as_of", label: t("common.as_of"), render: (v) => fmtDate(v.as_of) },
        {
          key: "provenance",
          label: t("common.provenance"),
          html: true,
          render: (v) => `${provenanceOf(v)} ${renderSourceRef(v.source_ref)}`,
          csv: (v) => `${v.held ? `held (${v.held_by})` : v.basis}${v.source_ref ? ` ${v.source_ref}` : ""}`,
        },
      ];
      return buildTable(`${dim.label_en}: ${t("screen2.distribution.title")}`, columns, reporting);
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
          { key: "value_type", label: "value_type", render: (v) => v.value_type ?? "" },
          { key: "held", label: "held_by", render: (v) => v.held_by ?? "" },
          { key: "source_ref", label: "source_slide", render: (v) => v.source_ref ?? "" },
        ],
        reporting,
      ),
    csvFilename: `indicator_${dim.indicator_code}_distribution`,
  });

  // ---- trend: small multiples, the countries with the richest history for
  // this indicator -- a pure count of non-null periods, not a ranking by
  // value (CLAUDE.md rule 5 is about comparing countries' figures, not
  // about which examples a design picks to illustrate a trend with).
  const nonNullPeriodsByCountry = new Map<string, number>();
  for (const v of values) {
    if (v.disagg_key !== "all" || v.value === null) continue;
    nonNullPeriodsByCountry.set(v.iso3, (nonNullPeriodsByCountry.get(v.iso3) ?? 0) + 1);
  }
  const trendCountries = [...nonNullPeriodsByCountry.keys()]
    .filter((iso3) => (nonNullPeriodsByCountry.get(iso3) ?? 0) >= MIN_TREND_PERIODS)
    .sort((a, b) => nameOf(a).localeCompare(nameOf(b))); // alphabetical, never in "most data" order

  const trendHost = container.querySelector("#trend-panel")!;
  if (trendCountries.length === 0) {
    trendHost.innerHTML = "";
  } else {
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
      const name = overview.countries.find((c) => c.iso3 === iso3)?.name ?? iso3;
      card.innerHTML = `<div class="trend-card__head">
          <span class="trend-card__name">${name}</span>
          ${latest ? provenanceOf(latest) : ""}
        </div>
        <div class="value-type">${valueTypeLabel(latest?.value_type, latest?.as_of)} ${renderSourceRef(latest?.source_ref)}</div>
        <div class="trend-card__value num">${latest ? fmtCount(latest.value) : NR}<small>${latest?.period_id ?? ""}</small></div>
        <div class="trend-card__chart"></div>`;
      card.querySelector(".trend-card__chart")!.appendChild(
        lineTrend(points, {
          valueLabel: activeDim.label_en,
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
