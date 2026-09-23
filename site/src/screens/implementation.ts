import { getImplementation } from "@/lib/bundle";
import { fmtCount } from "@/lib/format";
import { t } from "@/lib/i18n";
import { renderChartPanel } from "@/components/chart-panel";
import { renderStatus, statusFromImplementationStep, statusKey } from "@/lib/status";
import { panelTitleWithIcon, renderKpiCard, renderKpiRow } from "@/components/kpi";
import { buildTable, tableToCSVData, type Column } from "@/components/table";
import { buildPhaseGrid } from "@/components/phase-grid";
import { downloadCSV } from "@/components/csv";
import { horizontalBars, type BarDatum } from "@/charts/bar";
import type { ImplementationCountry } from "@/lib/types";

const PHASE_COUNT = 5;

function highestPhaseLabel(n: number): string {
  return n === 0 ? t("screen_impl.not_started") : t("screen_impl.phase_n", { n });
}

/**
 * Screen: "How far has each country gone?" -- the five implementation
 * phases and fourteen steps of Phase_1_PEN-Plus_Reporting_Tools.docx,
 * section 3. Distinct from `funding_round` (which Helmsley grant round a
 * country joined in): a country's phase progress is tracked here regardless
 * of round. Round 2 countries show "not yet reported" throughout -- the
 * round 2 form carries no implementation-phase question yet, and that gap
 * is real, not a loading error (see docs/architecture.md).
 *
 * Design review (expert panel, three independent reviewers) converged on one
 * finding: the full countries x steps grid is an audit view, not a briefing
 * view, and should not be the first thing this screen shows. The briefing
 * layer is the phase-distribution bar chart below the KPI row; the grid is
 * still here, in full, behind a closed-by-default disclosure, and built with
 * components/phase-grid.ts -- a grouped two-row header (which phase each
 * step belongs to) and a frozen country column, not a flat table.
 */
export async function renderImplementation(container: HTMLElement): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const bundle = await getImplementation();
  const { steps: stepDim, countries } = bundle;

  const reporting = countries.filter((c) => c.steps.some((s) => s.status !== null));
  const atFullScale = countries.filter((c) => c.highest_phase_completed === PHASE_COUNT).length;
  const notStarted = countries.filter((c) => c.highest_phase_completed === 0).length;
  const midOrFurther = countries.filter(
    (c) => c.highest_phase_completed > 0 && c.highest_phase_completed < PHASE_COUNT,
  ).length;

  container.innerHTML = `
    <h2 class="screen-title">${t("screen_impl.title")}</h2>
    <p class="panel__question">${t("screen_impl.question")}</p>

    ${renderKpiRow([
      renderKpiCard("country", fmtCount(reporting.length), t("screen_impl.kpi.reporting")),
      renderKpiCard("trend", String(midOrFurther), t("screen_impl.kpi.mid_scale_up")),
      renderKpiCard("shield", String(atFullScale), t("screen_impl.kpi.full_scale"), atFullScale === 0),
      renderKpiCard("alert", String(notStarted), t("screen_impl.kpi.not_started"), notStarted === 0),
    ])}

    <div id="phase-summary-panel"></div>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("grid", t("screen_impl.grid.title"))}</div>
      <p class="chart-caption">${t("screen_impl.grid.caption")}</p>
      <dl class="definition-panel" id="phase-legend"></dl>
      <div class="chart-legend">
        <span class="chart-legend__item">${renderStatus("met", t("status.met"))}</span>
        <span class="chart-legend__item">${renderStatus("partly_met", t("status.partly_met"))}</span>
        <span class="chart-legend__item">${renderStatus("not_met", t("status.not_met"))}</span>
        <span class="chart-legend__item">${renderStatus("not_reported", t("status.not_reported"))}</span>
      </div>
      <details id="grid-detail">
        <summary class="btn">${t("screen_impl.grid.show_detail")}</summary>
        <div class="toolbar"><button type="button" class="btn" id="export-btn">${t("common.export_csv")}</button></div>
        <div id="implementation-table"></div>
      </details>
    </section>
  `;

  // ---- phase-distribution summary: the briefing layer. Pure counts per
  // bucket (0..5), the same kind of client-side .filter().length already
  // used for the KPI cards above -- never a ranking of individual countries,
  // and never a mean (a mean over an ordinal stage code implies false
  // interval-scale precision, and was computed client-side, which CLAUDE.md's
  // no-arithmetic-in-the-front-end rule does not allow -- removed, not moved).
  const bucketData: BarDatum[] = [0, 1, 2, 3, 4, 5].map((n) => {
    const count = countries.filter((c) => c.highest_phase_completed === n).length;
    const label = highestPhaseLabel(n);
    return { label, value: count, title: `${label}: ${count}` };
  });
  renderChartPanel(container.querySelector("#phase-summary-panel")!, {
    title: t("screen_impl.summary.title"),
    icon: "target",
    caption: t("screen_impl.summary.caption"),
    buildChart: () =>
      horizontalBars(bucketData, { valueLabel: t("screen_impl.kpi.reporting_short"), height: 220 }),
    buildTable: () =>
      buildTable(
        t("screen_impl.summary.title"),
        [
          { key: "label", label: t("screen_impl.column.highest_phase"), render: (d: BarDatum) => d.label },
          {
            key: "value",
            label: t("common.select_country"),
            numeric: true,
            render: (d: BarDatum) => String(d.value),
          },
        ],
        bucketData,
      ),
    csv: () =>
      tableToCSVData<BarDatum>(
        [
          { key: "label", label: "highest_phase", render: (d) => d.label },
          { key: "value", label: "countries", render: (d) => String(d.value) },
        ],
        bucketData,
      ),
    csvFilename: "implementation_phase_summary",
  });

  // ---- phase/step legend, above the detail table so a reader meets it
  // before the grid rather than after scrolling past it
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

  // Columns for CSV export only -- the visual table is components/phase-grid.ts,
  // built directly from stepDim/countries, not from this Column[] list.
  const csvColumns: Column<ImplementationCountry>[] = [
    { key: "name", label: t("common.select_country"), render: (c) => c.name },
    {
      key: "highest_phase_completed",
      label: t("screen_impl.column.highest_phase"),
      render: (c) => highestPhaseLabel(c.highest_phase_completed),
    },
    ...stepDim.map((s): Column<ImplementationCountry> => {
      const row = (c: ImplementationCountry) => c.steps.find((r) => r.step_no === s.step_no);
      return {
        key: `step_${s.step_no}`,
        label: String(s.step_no),
        render: (c) => t(statusKey(statusFromImplementationStep(row(c)?.status ?? null))),
        csv: (c) => row(c)?.status ?? "not_reported",
      };
    }),
  ];

  const sorted = [...countries].sort((a, b) => a.name.localeCompare(b.name));
  const tableHost = container.querySelector("#implementation-table")!;
  const detail = container.querySelector<HTMLDetailsElement>("#grid-detail")!;

  let built = false;
  function buildGridOnce() {
    if (built) return;
    built = true;
    tableHost.appendChild(buildPhaseGrid(t("screen_impl.grid.title"), stepDim, sorted));
  }
  // Build the (large) grid lazily, only once a reader actually opens the
  // disclosure -- most visits to this screen should never pay for it.
  detail.addEventListener("toggle", buildGridOnce, { once: true });

  container.querySelector("#export-btn")!.addEventListener("click", () => {
    const { headers, rows } = tableToCSVData<ImplementationCountry>(csvColumns, sorted);
    downloadCSV("implementation_phases", headers, rows);
  });
}
