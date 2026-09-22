import { getOverview, getQuality } from "@/lib/bundle";
import { fmtCompletenessShare, fmtDate, fmtNandN, NR } from "@/lib/format";
import { t } from "@/lib/i18n";
import { renderChartPanel } from "@/components/chart-panel";
import { renderCompleteness } from "@/components/completeness";
import { renderStatus } from "@/lib/status";
import { panelTitleWithIcon, renderKpiCard, renderKpiRow } from "@/components/kpi";
import { buildTable, tableToCSVData, type Column } from "@/components/table";
import { dotPlot, type DotDatum } from "@/charts/dotplot";
import { severityKey, verdictKey } from "@/lib/vocab";
import type { OpenQuery, QualityRow } from "@/lib/types";

export async function renderDataQuality(container: HTMLElement): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const [quality, overview] = await Promise.all([getQuality(), getOverview()]);
  const nameByIso3 = new Map(overview.countries.map((c) => [c.iso3, c.name]));

  // computed ahead of the template so the KPI row can read from it
  const latestByCountry = new Map<string, QualityRow>();
  for (const row of quality.rows) {
    const prev = latestByCountry.get(row.iso3);
    if (!prev || row.period_id > prev.period_id) latestByCountry.set(row.iso3, row);
  }
  const latestRows = [...latestByCountry.values()];
  // avg_completeness and countries_below_threshold are computed once in
  // export.py over each country's latest period, not re-derived here
  // (CLAUDE.md rule 1: no arithmetic in the front end).
  const avgCompleteness = quality.avg_completeness;
  const belowThreshold = quality.countries_below_threshold;
  const highSeverity = quality.open_queries.filter((q) => q.severity === "High").length;

  container.innerHTML = `
    <h2 class="screen-title">${t("screen4.title")}</h2>
    <p class="panel__question">${t("screen4.question")}</p>

    ${renderKpiRow([
      renderKpiCard(
        "shield",
        avgCompleteness === null ? NR : `${Math.round(avgCompleteness * 100)}%`,
        t("screen4.kpi.avg_completeness"),
        avgCompleteness === null,
      ),
      renderKpiCard("alert", String(belowThreshold), t("screen4.kpi.below_threshold"), belowThreshold === 0),
      renderKpiCard(
        "flag",
        String(quality.open_queries.length),
        t("common.open_queries"),
        quality.open_queries.length === 0,
      ),
      renderKpiCard("alert", String(highSeverity), t("screen4.kpi.high_severity"), highSeverity === 0),
    ])}

    <div id="completeness-panel"></div>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("grid", t("screen4.completeness.title"))}</div>
      <label class="history-toggle"><input type="checkbox" id="history-toggle" /> ${t("screen4.show_history")}</label>
      <div id="quality-table"></div>
    </section>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("alert", t("screen4.queries.title"))}</div>
      <div class="screen-controls">
        <label>${t("table.severity")} <select id="severity-filter">
          <option value="">${t("common.all")}</option>
          <option value="High">${t("severity.high")}</option>
          <option value="Medium">${t("severity.medium")}</option>
          <option value="Low">${t("severity.low")}</option>
        </select></label>
      </div>
      <div id="queries-table"></div>
    </section>
  `;

  const dotData: DotDatum[] = latestRows
    .filter((r) => r.completeness !== null)
    .map((r) => ({
      label: nameByIso3.get(r.iso3) ?? r.iso3,
      value: Math.round((r.completeness ?? 0) * 100),
    }));

  renderChartPanel(container.querySelector("#completeness-panel")!, {
    title: t("screen4.completeness.title"),
    icon: "shield",
    caption: t("screen4.completeness.title") + " (%). " + t("empty.no_data"),
    buildChart: () => dotPlot(dotData, { valueLabel: "% complete" }),
    buildTable: () =>
      buildTable(
        t("screen4.completeness.title"),
        [
          { key: "label", label: t("common.select_country"), render: (d: DotDatum) => d.label },
          { key: "value", label: "%", numeric: true, render: (d: DotDatum) => String(d.value) },
        ],
        dotData,
      ),
    csv: () =>
      tableToCSVData<DotDatum>(
        [
          { key: "label", label: "country", render: (d) => d.label },
          { key: "value", label: "completeness_pct", render: (d) => String(d.value) },
        ],
        dotData,
      ),
    csvFilename: "quality_completeness",
  });

  // ---- full completeness / confidence / definition-compliance table
  const qColumns: Column<QualityRow>[] = [
    { key: "iso3", label: t("common.select_country"), render: (r) => nameByIso3.get(r.iso3) ?? r.iso3 },
    { key: "period_id", label: t("common.select_period"), render: (r) => r.period_id },
    {
      key: "verdict",
      label: t("table.status"),
      html: true,
      render: (r) =>
        r.verdict === "hold"
          ? renderStatus("awaiting_clarification", t("status.awaiting_clarification"))
          : `<span class="chip">${t(verdictKey(r.verdict))}</span>`,
      csv: (r) => r.verdict,
    },
    {
      key: "completeness",
      label: t("table.completeness"),
      numeric: true,
      render: (r) => (r.completeness === null ? NR : renderCompleteness(r.completeness)),
      html: true,
      csv: (r) => fmtCompletenessShare(r.completeness),
    },
    {
      key: "returns_on_time",
      label: t("table.on_time"),
      render: (r) =>
        r.returns_on_time === null || r.facilities_expected === null
          ? NR
          : fmtNandN(r.returns_on_time, r.facilities_expected),
    },
    {
      key: "ltfu_compliant",
      label: t("table.ltfu_rule"),
      render: (r) => (r.ltfu_compliant === null ? NR : r.ltfu_compliant ? t("common.yes") : t("common.no")),
    },
    { key: "conf_patients", label: t("table.confidence_patients"), render: (r) => r.conf_patients ?? NR },
    {
      key: "source_kind",
      label: t("common.historical"),
      render: (r) => (r.source_kind === "historical" ? t("common.historical") : ""),
    },
    {
      key: "open_queries",
      label: t("common.open_queries"),
      numeric: true,
      render: (r) => String(r.open_queries),
    },
  ];
  const sortedLatest = [...latestRows].sort((a, b) => a.iso3.localeCompare(b.iso3));
  const sortedAll = [...quality.rows].sort(
    (a, b) => a.iso3.localeCompare(b.iso3) || a.period_id.localeCompare(b.period_id),
  );
  function renderQualityTable(showFullHistory: boolean) {
    container
      .querySelector("#quality-table")!
      .replaceChildren(
        buildTable(
          showFullHistory ? t("screen4.completeness.title_all") : t("screen4.completeness.title_latest"),
          qColumns,
          showFullHistory ? sortedAll : sortedLatest,
        ),
      );
  }
  container.querySelector<HTMLInputElement>("#history-toggle")!.addEventListener("change", (e) => {
    renderQualityTable((e.target as HTMLInputElement).checked);
  });
  renderQualityTable(false);

  // ---- open query register
  function renderQueries(severity: string) {
    const rows = quality.open_queries.filter((q) => !severity || q.severity === severity);
    const columns: Column<OpenQuery>[] = [
      { key: "iso3", label: t("common.select_country"), render: (q) => nameByIso3.get(q.iso3) ?? q.iso3 },
      { key: "period_id", label: t("common.select_period"), render: (q) => q.period_id },
      { key: "severity", label: t("table.severity"), render: (q) => t(severityKey(q.severity)) },
      { key: "section", label: t("table.section"), render: (q) => q.section },
      { key: "field", label: t("table.field"), render: (q) => q.field },
      { key: "question", label: t("table.question"), render: (q) => q.question },
      { key: "raised_at", label: t("common.as_of"), render: (q) => fmtDate(q.raised_at) },
    ];
    const host = container.querySelector("#queries-table")!;
    host.replaceChildren(
      rows.length
        ? buildTable(t("screen4.queries.title"), columns, rows)
        : Object.assign(document.createElement("p"), {
            className: "callout callout--empty",
            textContent: t("common.no_open_queries"),
          }),
    );
  }
  container.querySelector<HTMLSelectElement>("#severity-filter")!.addEventListener("change", (e) => {
    renderQueries((e.target as HTMLSelectElement).value);
  });
  renderQueries("");
}
