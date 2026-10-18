import { getQuality } from "@/lib/bundle";
import { fmtCount, fmtDate } from "@/lib/format";
import { t } from "@/lib/i18n";
import { panelTitleWithIcon, renderKpiCard, renderKpiRow } from "@/components/kpi";
import { buildTable, tableToCSVData, type Column } from "@/components/table";
import { downloadCSV } from "@/components/csv";
import { renderProvenance } from "@/components/provenance";
import { renderQueryList, sortQueries } from "@/components/queries";
import { severityKey } from "@/lib/vocab";
import type { CheckSummary, CoverageCell, ProvenanceRow, Query } from "@/lib/types";

/** Coverage matrix cell: a shape and a word, never colour alone (rule 9). */
const CELL_MARK: Record<CoverageCell, string> = { value: "●", held: "◆", not_reported: "○" };

/**
 * Screen 4: "How much of this can be trusted?" Rebuilt to
 * docs/refinement/04_data_quality/DATA_QUALITY_SPEC.md. No card reads "0"
 * where the truth is "not measurable"; all 31 countries always appear;
 * nothing is called "Accepted" that was not tested. Every count is
 * computed in export.py.
 */
export async function renderDataQuality(container: HTMLElement): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const q = await getQuality();
  const k = q.kpis;
  const validatedCard =
    k.validated_returns.period === null
      ? renderKpiCard(
          "shield",
          t("common.n_of_total", { n: k.validated_returns.n, total: k.validated_returns.total }),
          t("screen4.kpi.validated_none"),
          true,
        )
      : renderKpiCard(
          "shield",
          t("common.n_of_total", { n: k.validated_returns.n, total: k.validated_returns.total }),
          t("screen4.kpi.validated", { period: k.validated_returns.period }),
        );

  container.innerHTML = `
    <header class="page-head">
      <h2 class="screen-title">${t("screen4.title")}</h2>
      <p class="panel__question">${t("screen4.question")}</p>
    </header>

    ${renderKpiRow([
      validatedCard,
      renderKpiCard(
        "alert",
        fmtCount(k.held_figures.n + k.held_figures.regional),
        t("screen4.kpi.held", { countries: k.held_figures.n, regional: k.held_figures.regional }),
      ),
      renderKpiCard(
        "flag",
        fmtCount(k.open_queries.total),
        t("screen4.kpi.open_queries", {
          high: k.open_queries.High,
          medium: k.open_queries.Medium,
          low: k.open_queries.Low,
        }),
      ),
      renderKpiCard(
        "grid",
        t("common.n_of_total", { n: k.indicators_covered.n, total: k.indicators_covered.total }),
        t("screen4.kpi.coverage80"),
      ),
    ])}

    <p class="exec-message">${t("screen4.summary_v2", {
      validated: k.validated_returns.n,
      queries: k.open_queries.total,
      high: k.open_queries.High,
      closed: k.queries_closed,
    })}</p>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("country", t("screen4.provenance.title"))}
        <button type="button" class="btn" id="prov-export">${t("common.export_csv")}</button></div>
      <p class="chart-caption">${t("screen4.provenance.caption")}</p>
      <div id="provenance-table"></div>
    </section>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("grid", t("screen4.coverage.title"))}</div>
      <p class="chart-caption">${t("screen4.coverage.caption")}</p>
      <div class="chart-legend">
        <span class="chart-legend__item"><span class="cov cov--value">${CELL_MARK.value}</span>${t("screen4.coverage.value")}</span>
        <span class="chart-legend__item"><span class="cov cov--held">${CELL_MARK.held}</span>${t("prov.held")}</span>
        <span class="chart-legend__item"><span class="cov cov--not_reported">${CELL_MARK.not_reported}</span>${t("status.not_reported")}</span>
      </div>
      <div id="coverage-matrix" class="data-table-wrap"></div>
    </section>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("shield", t("screen4.checks.title"))}</div>
      <p class="chart-caption">${t("screen4.checks.caption")}</p>
      <div id="checks-table"></div>
      <div id="check-failures"></div>
    </section>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("alert", t("screen4.held.title"))}</div>
      <div id="held-list"></div>
    </section>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("flag", t("screen4.queries.title"))}
        <button type="button" class="btn" id="queries-export">${t("common.export_csv")}</button></div>
      <div class="screen-controls">
        <label>${t("table.severity")} <select id="severity-filter">
          <option value="">${t("common.all")}</option>
          <option value="High">${t("severity.high")}</option>
          <option value="Medium">${t("severity.medium")}</option>
          <option value="Low">${t("severity.low")}</option>
        </select></label>
        <label>${t("common.select_country")} <select id="country-filter">
          <option value="">${t("common.all_countries")}</option>
        </select></label>
        <label>${t("table.status")} <select id="status-filter">
          <option value="open">${t("query_status.open")}</option>
          <option value="">${t("common.all")}</option>
          <option value="closed">${t("query_status.closed")}</option>
        </select></label>
      </div>
      <div id="queries-list"></div>
    </section>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("shield", t("screen4.dsa.title"))}</div>
      <div id="dsa-cards" class="dsa-grid"></div>
      <p class="chart-caption">${t("screen4.dsa.missing", { n: q.data_systems_missing.length })}</p>
      <div class="pill-list">${q.data_systems_missing.map((n) => `<span class="pill pill--nr">${n}</span>`).join("")}</div>
    </section>
  `;

  // ---- 4.2 evidence provenance: all 31 countries, one row each
  const provColumns: Column<ProvenanceRow>[] = [
    { key: "name", label: t("common.select_country"), render: (r) => r.name },
    {
      key: "cohort",
      label: t("table.cohort"),
      render: (r) => t(r.cohort === "phase_1" ? "common.phase1" : "common.phase2"),
    },
    {
      key: "source",
      label: t("table.evidence_source"),
      render: (r) => t(`evidence_source.${r.evidence_source}`),
    },
    { key: "period", label: t("table.latest_period"), render: (r) => r.latest_period ?? "NR" },
    {
      key: "types",
      label: t("common.value_type"),
      render: (r) => (r.value_types.length ? r.value_types.join(", ") : "NR"),
    },
    {
      key: "queries",
      label: t("common.open_queries"),
      html: true,
      render: (r) =>
        r.open_queries === 0
          ? "0"
          : `${r.open_queries} <span class="sev sev--${r.highest_severity!.toLowerCase()}">${t(severityKey(r.highest_severity!))}</span>`,
      csv: (r) => `${r.open_queries}${r.highest_severity ? ` (${r.highest_severity})` : ""}`,
    },
    {
      key: "status",
      label: t("table.status"),
      html: true,
      render: (r) => renderProvenance(r.status),
      csv: (r) => r.status,
    },
  ];
  container
    .querySelector("#provenance-table")!
    .appendChild(buildTable(t("screen4.provenance.title"), provColumns, q.provenance));
  container.querySelector("#prov-export")!.addEventListener("click", () => {
    const { headers, rows } = tableToCSVData(provColumns, q.provenance);
    downloadCSV("evidence_provenance", headers, rows);
  });

  // ---- 4.3 coverage matrix: countries x the 16 indicators
  const ind = q.coverage.indicators;
  const matrix = document.createElement("table");
  matrix.className = "data-table coverage-matrix";
  matrix.innerHTML = `<caption>${t("screen4.coverage.title")}</caption>
    <thead>
      <tr><th scope="col">${t("common.select_country")}</th>${ind
        .map(
          (i) =>
            `<th scope="col" class="cov-head" title="${i.label_en.replace(/"/g, "&quot;")}">${i.indicator_code}</th>`,
        )
        .join("")}</tr>
    </thead>
    <tbody>${q.coverage.rows
      .map(
        (r) =>
          `<tr><th scope="row">${r.name}</th>${ind
            .map((i) => {
              const cell = r.cells[i.indicator_code] ?? "not_reported";
              const word =
                cell === "value"
                  ? t("screen4.coverage.value")
                  : cell === "held"
                    ? t("prov.held")
                    : t("status.not_reported");
              return `<td class="cov cov--${cell}" title="${r.name}, ${i.indicator_code}: ${word}"><span aria-label="${word}">${CELL_MARK[cell]}</span></td>`;
            })
            .join("")}</tr>`,
      )
      .join("")}</tbody>
    <tfoot><tr><th scope="row">${t("screen4.coverage.countries_with_value")}</th>${ind
      .map((i) => `<td class="num">${i.countries_with_value}</td>`)
      .join("")}</tr></tfoot>`;
  container.querySelector("#coverage-matrix")!.appendChild(matrix);

  // ---- 4.4 validation checks; a rule with failures lists them on click
  const failuresHost = container.querySelector<HTMLElement>("#check-failures")!;
  const checkColumns: Column<CheckSummary>[] = [
    { key: "rule", label: t("table.rule"), render: (c) => c.rule },
    { key: "check", label: t("table.check"), render: (c) => c.check },
    {
      key: "severity",
      label: t("table.severity"),
      html: true,
      render: (c) =>
        `<span class="sev sev--${c.severity.toLowerCase()}">${t(severityKey(c.severity))}</span>`,
      csv: (c) => c.severity,
    },
    { key: "passed", label: t("screen4.checks.passed"), numeric: true, render: (c) => String(c.passed) },
    {
      key: "failed",
      label: t("screen4.checks.failed"),
      numeric: true,
      html: true,
      render: (c) =>
        c.failed > 0
          ? `<button type="button" class="link-btn" data-rule="${c.rule}">${c.failed}</button>`
          : "0",
      csv: (c) => String(c.failed),
    },
    {
      key: "not_testable",
      label: t("screen4.checks.not_testable"),
      numeric: true,
      render: (c) => String(c.not_testable),
    },
  ];
  const checksHost = container.querySelector("#checks-table")!;
  checksHost.appendChild(buildTable(t("screen4.checks.title"), checkColumns, q.checks));
  checksHost.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>("button[data-rule]");
    if (!btn) return;
    const rule = q.checks.find((c) => c.rule === btn.dataset.rule);
    if (!rule) return;
    failuresHost.innerHTML = `<div class="callout callout--flag"><strong>${rule.rule}: ${rule.check}</strong>
      <ul>${rule.failures.map((f) => `<li>${f.iso3} ${f.period_id}: ${f.detail ?? ""}</li>`).join("")}</ul></div>`;
  });

  // ---- held figures: listed, never silently dropped
  const heldHost = container.querySelector("#held-list")!;
  const heldItems = [
    ...q.held_regional.map(
      (h) =>
        `<li><b>${t("screen4.held.regional", { code: h.indicator_code })}</b> <span class="prov prov--held">${h.held_by}</span></li>`,
    ),
    ...q.held_figures.map(
      (h) =>
        `<li><b>${h.iso3} ${h.indicator_code}</b> ${h.period_id}: ${fmtCount(h.value)} <span class="prov prov--held">${h.held_by ?? ""}</span></li>`,
    ),
  ];
  heldHost.innerHTML =
    heldItems.length === 0
      ? `<p class="callout callout--empty">${t("screen4.held.none")}</p>`
      : `<p class="chart-caption">${t("screen4.held.caption")}</p><ul class="held-list">${heldItems.join("")}</ul>`;

  // ---- 4.5 query register: seeded + pipeline findings, filters, CSV
  const countrySel = container.querySelector<HTMLSelectElement>("#country-filter")!;
  const scopes = [...new Set(q.queries.flatMap((x) => x.scope.split(";").map((s) => s.trim())))].sort();
  for (const s of scopes) {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s === "REG" ? t("common.regional") : s;
    countrySel.appendChild(opt);
  }
  const sevSel = container.querySelector<HTMLSelectElement>("#severity-filter")!;
  const statusSel = container.querySelector<HTMLSelectElement>("#status-filter")!;
  const filtered = (): Query[] =>
    sortQueries(
      q.queries.filter(
        (x) =>
          (!sevSel.value || x.severity === sevSel.value) &&
          (!statusSel.value || x.status === statusSel.value) &&
          (!countrySel.value ||
            x.scope
              .split(";")
              .map((s) => s.trim())
              .includes(countrySel.value)),
      ),
    );
  const queriesHost = container.querySelector("#queries-list")!;
  const drawQueries = () => {
    const rows = filtered();
    queriesHost.innerHTML =
      rows.length === 0
        ? `<p class="callout callout--empty">${t("screen4.queries.none_match")}</p>`
        : renderQueryList(rows);
  };
  [sevSel, statusSel, countrySel].forEach((s) => s.addEventListener("change", drawQueries));
  drawQueries();
  const queryCsv: Column<Query>[] = [
    { key: "query_id", label: "query_id", render: (x) => x.query_id },
    { key: "scope", label: "country", render: (x) => x.scope },
    { key: "indicator", label: "indicator", render: (x) => x.indicator ?? "" },
    { key: "severity", label: "severity", render: (x) => x.severity },
    { key: "issue", label: "issue", render: (x) => x.issue ?? "" },
    { key: "evidence", label: "evidence", render: (x) => x.evidence ?? "" },
    { key: "action", label: "action", render: (x) => x.action ?? "" },
    { key: "status", label: "status", render: (x) => x.status },
    { key: "resolution", label: "resolution", render: (x) => x.resolution ?? "" },
    { key: "opened_on", label: "date_opened", render: (x) => x.opened_on ?? "" },
  ];
  container.querySelector("#queries-export")!.addEventListener("click", () => {
    const { headers, rows } = tableToCSVData(queryCsv, filtered());
    downloadCSV("query_register", headers, rows);
  });

  // ---- 4.6 country data-system readiness (no respondent names, ever)
  container.querySelector("#dsa-cards")!.innerHTML = q.data_systems
    .map(
      (d) => `<div class="dsa-card">
        <h4>${d.name ?? d.iso3}</h4>
        <p class="chart-caption">${t("screen4.dsa.caption", { date: fmtDate(d.assessed_on), institution: d.institution ?? "" })}</p>
        <dl>${Object.entries(d.fields)
          .map(([key, v]) => `<dt>${t(`dsa.${key}`)}</dt><dd>${v}</dd>`)
          .join("")}</dl>
      </div>`,
    )
    .join("");
}
