import { getOverview, getQuality } from "@/lib/bundle";
import { fmtCompletenessShare, fmtDate, NR } from "@/lib/format";
import { t } from "@/lib/i18n";
import { renderChartPanel } from "@/components/chart-panel";
import { renderCompleteness } from "@/components/completeness";
import { renderStatus, statusFromVerdict, statusKey } from "@/lib/status";
import { buildTable, tableToCSVData, type Column } from "@/components/table";
import { dotPlot, type DotDatum } from "@/charts/dotplot";
import { severityKey } from "@/lib/vocab";
import type { OpenQuery, QualityRow } from "@/lib/types";

export async function renderDataQuality(container: HTMLElement): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const [quality, overview] = await Promise.all([getQuality(), getOverview()]);
  const nameByIso3 = new Map(overview.countries.map((c) => [c.iso3, c.name]));

  container.innerHTML = `
    <h2 class="screen-title">${t("screen4.title")}</h2>
    <p class="panel__question">${t("screen4.question")}</p>

    <div id="completeness-panel"></div>

    <section class="panel">
      <div class="panel__header"><h3 class="panel__title">${t("screen4.completeness.title")}</h3></div>
      <div id="quality-table"></div>
    </section>

    <section class="panel">
      <div class="panel__header"><h3 class="panel__title">${t("screen4.queries.title")}</h3></div>
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

  // ---- completeness distribution, most recent period per country
  const latestByCountry = new Map<string, QualityRow>();
  for (const row of quality.rows) {
    const prev = latestByCountry.get(row.iso3);
    if (!prev || row.period_id > prev.period_id) latestByCountry.set(row.iso3, row);
  }
  const dotData: DotDatum[] = [...latestByCountry.values()]
    .filter((r) => r.completeness !== null)
    .map((r) => ({
      label: nameByIso3.get(r.iso3) ?? r.iso3,
      value: Math.round((r.completeness ?? 0) * 100),
    }));

  renderChartPanel(container.querySelector("#completeness-panel")!, {
    title: t("screen4.completeness.title"),
    caption: t("screen4.completeness.title") + " (%) — " + t("empty.no_data"),
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
      render: (r) => renderStatus(statusFromVerdict(r.verdict), t(statusKey(statusFromVerdict(r.verdict)))),
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
  container.querySelector("#quality-table")!.appendChild(
    buildTable(
      t("screen4.completeness.title"),
      qColumns,
      [...quality.rows].sort(
        (a, b) => a.iso3.localeCompare(b.iso3) || a.period_id.localeCompare(b.period_id),
      ),
    ),
  );

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
