import { getImplementation } from "@/lib/bundle";
import { fmtCount, fmtDate, NR } from "@/lib/format";
import { t } from "@/lib/i18n";
import { navigate } from "@/router";
import { renderStatus, statusFromImplementationStep, statusKey } from "@/lib/status";
import { panelTitleWithIcon, renderKpiCard, renderKpiRow } from "@/components/kpi";
import { buildPaginatedTable, tableToCSVData, type Column } from "@/components/table";
import { downloadCSV } from "@/components/csv";
import type { ImplementationCountry, ImplementationStepDim } from "@/lib/types";

const PHASE_COUNT = 5;

/**
 * A single glyph per status for the grid's narrow step columns. Not the
 * first letter of the translated label: "Not met" and "Not reported" both
 * start with "N" in English (and "Non atteint"/"Non déclaré" both start
 * with "N" in French), which would make two different statuses render the
 * same letter -- the status mark's shape and colour already differ
 * (components.css, `.status--*::before`), but the accessible text (the
 * `title` attribute, which carries the full word) must not collide too.
 */
const STATUS_MARK: Record<string, string> = {
  met: "✓",
  partly_met: "~",
  not_met: "✗",
  not_reported: "·",
};

function highestPhaseLabel(n: number): string {
  return n === 0 ? t("screen_impl.not_started") : t("screen_impl.phase_n", { n });
}

/**
 * Screen: "How far has each country gone?" -- the five implementation
 * phases and fourteen steps of Phase_1_PEN-Plus_Reporting_Tools.docx,
 * section 3, one column per step grouped under its phase, one row per
 * country. Distinct from `funding_round` (which Helmsley grant round a
 * country joined in): a country's phase progress is tracked here regardless
 * of round. Round 2 countries show "not yet reported" throughout -- the
 * round 2 form carries no implementation-phase question yet, and that gap
 * is real, not a loading error (see docs/architecture.md).
 */
export async function renderImplementation(container: HTMLElement): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const bundle = await getImplementation();
  const { steps: stepDim, countries } = bundle;

  const reporting = countries.filter((c) => c.steps.some((s) => s.status !== null));
  const atFullScale = countries.filter((c) => c.highest_phase_completed === PHASE_COUNT).length;
  const notStarted = countries.filter((c) => c.highest_phase_completed === 0).length;
  const avgPhase =
    reporting.length > 0
      ? reporting.reduce((sum, c) => sum + c.highest_phase_completed, 0) / reporting.length
      : null;

  container.innerHTML = `
    <h2 class="screen-title">${t("screen_impl.title")}</h2>
    <p class="panel__question">${t("screen_impl.question")}</p>

    ${renderKpiRow([
      renderKpiCard("country", fmtCount(reporting.length), t("screen_impl.kpi.reporting")),
      renderKpiCard(
        "flag",
        avgPhase === null ? NR : avgPhase.toFixed(1),
        t("screen_impl.kpi.avg_phase"),
        avgPhase === null,
      ),
      renderKpiCard("shield", String(atFullScale), t("screen_impl.kpi.full_scale"), atFullScale === 0),
      renderKpiCard("alert", String(notStarted), t("screen_impl.kpi.not_started"), notStarted === 0),
    ])}

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("grid", t("screen_impl.grid.title"))}</div>
      <p class="chart-caption">${t("screen_impl.grid.caption")}</p>
      <div class="chart-legend">
        <span class="chart-legend__item">${renderStatus("met", t("status.met"))}</span>
        <span class="chart-legend__item">${renderStatus("partly_met", t("status.partly_met"))}</span>
        <span class="chart-legend__item">${renderStatus("not_met", t("status.not_met"))}</span>
        <span class="chart-legend__item">${renderStatus("not_reported", t("status.not_reported"))}</span>
      </div>
      <div class="toolbar"><button type="button" class="btn" id="export-btn">${t("common.export_csv")}</button></div>
      <div id="implementation-table"></div>
      <dl class="definition-panel" id="phase-legend"></dl>
    </section>
  `;

  const legend = container.querySelector("#phase-legend")!;
  const phaseNos = [...new Set(stepDim.map((s) => s.phase_no))].sort((a, b) => a - b);
  for (const phaseNo of phaseNos) {
    const phaseLabel = stepDim.find((s) => s.phase_no === phaseNo)!.phase_label;
    const stepsOfPhase = stepDim.filter((s) => s.phase_no === phaseNo);
    const dt = document.createElement("dt");
    dt.textContent = phaseLabel;
    const dd = document.createElement("dd");
    dd.textContent = stepsOfPhase.map((s) => `${s.step_no}. ${s.step_label}`).join("; ");
    legend.append(dt, dd);
  }

  const columns: Column<ImplementationCountry>[] = [
    { key: "name", label: t("common.select_country"), render: (c) => c.name },
    {
      key: "highest_phase_completed",
      label: t("screen_impl.column.highest_phase"),
      html: true,
      render: (c) => `<span class="chip">${highestPhaseLabel(c.highest_phase_completed)}</span>`,
      csv: (c) => highestPhaseLabel(c.highest_phase_completed),
    },
    ...stepDim.map((s: ImplementationStepDim): Column<ImplementationCountry> => ({
      key: `step_${s.step_no}`,
      label: String(s.step_no),
      html: true,
      render: (c) => {
        const row = c.steps.find((r) => r.step_no === s.step_no);
        const status = statusFromImplementationStep(row?.status ?? null);
        const title = [
          `${s.phase_label}: ${s.step_no}. ${s.step_label}`,
          t(statusKey(status)),
          row?.as_of ? `${t("common.as_of")} ${fmtDate(row.as_of)}` : "",
          row?.source ?? "",
        ]
          .filter(Boolean)
          .join(" · ");
        return `<span title="${title.replace(/"/g, "&quot;")}">${renderStatus(status, STATUS_MARK[status] ?? "?")}</span>`;
      },
      csv: (c) => {
        const row = c.steps.find((r) => r.step_no === s.step_no);
        return row?.status ?? "not_reported";
      },
    })),
  ];

  const sorted = [...countries].sort((a, b) => a.name.localeCompare(b.name));
  const tableHost = container.querySelector("#implementation-table")!;
  tableHost.appendChild(buildPaginatedTable(t("screen_impl.grid.title"), columns, sorted));

  // clicking a country's name row navigates to its profile, mirroring the
  // overview screen's country tiles
  tableHost.querySelectorAll("tbody tr").forEach((tr, i) => {
    const c = sorted[i];
    if (!c) return;
    tr.addEventListener("click", () => navigate({ screen: "country", iso3: c.iso3 }));
    (tr as HTMLElement).style.cursor = "pointer";
  });

  container.querySelector("#export-btn")!.addEventListener("click", () => {
    const { headers, rows } = tableToCSVData<ImplementationCountry>(columns, sorted);
    downloadCSV("implementation_phases", headers, rows);
  });
}
