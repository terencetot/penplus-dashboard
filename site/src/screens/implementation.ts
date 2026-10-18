import { getImplementation } from "@/lib/bundle";
import { fmtCount } from "@/lib/format";
import { t } from "@/lib/i18n";
import { renderStatus, statusFromImplementationStep, statusKey } from "@/lib/status";
import { panelTitleWithIcon } from "@/components/kpi";
import { statTile } from "@/components/stat";
import { loadWhoGeo, PHASE_COLOURS, renderPhaseMap } from "@/components/facility-map";
import { countryName, phaseLabel, stepLabel } from "@/lib/names";
import { tableToCSVData, type Column } from "@/components/table";
import { buildPhaseGrid } from "@/components/phase-grid";
import { downloadCSV } from "@/components/csv";
import type { ImplementationCountry } from "@/lib/types";

function phaseShort(n: number | null): string {
  return n === null ? t("prov.no_return") : t("screen_impl.phase_n", { n });
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

  // Every count below is computed in export.py (phase_counts, no_return,
  // disagreements); the screen only reads them.
  const withPhase = bundle.with_phase;
  const national = bundle.phase_counts.find((p) => p.phase === 5)?.countries ?? 0;
  const phase4 = bundle.phase_counts.find((p) => p.phase === 4)?.countries ?? 0;
  const geo = await loadWhoGeo();

  container.innerHTML = `
    <header class="page-head">
      <h2 class="screen-title">${t("screen_impl.title")}</h2>
      <p class="panel__question">${t("screen_impl.question")}</p>
    </header>

    <div class="stat-row stat-row--4">
      ${statTile(t("screen_impl.kpi.with_phase"), `${fmtCount(withPhase)}<small>/${countries.length}</small>`, t("screen_impl.kpi.with_phase_sub"))}
      ${statTile(t("screen_impl.kpi.full_scale"), String(national), t("screen_impl.kpi.full_scale_sub"))}
      ${statTile(t("screen_impl.kpi.phase4"), String(phase4), t("screen_impl.kpi.phase4_sub"))}
      ${statTile(t("screen_impl.kpi.no_return"), String(bundle.no_return), t("screen_impl.kpi.no_return_sub"))}
    </div>

    <section class="panel phase-map-panel">
      <div class="panel__header">${panelTitleWithIcon("map", t("screen_impl.map.title"))}</div>
      <div class="phase-map-layout">
        <div id="phase-map" class="phase-map"></div>
        <div class="phase-legend">
          ${[5, 4, 3, 2, 1]
            .map(
              (n) => `<div class="phase-legend__row"><i style="background:${PHASE_COLOURS[n - 1]}"></i>
                <span><b>${t("screen_impl.phase_n", { n })}</b> ${t(`screen3.phase_name.${n}`)}</span>
                <em class="num">${bundle.phase_counts.find((p) => p.phase === n)?.countries ?? 0}</em></div>`,
            )
            .join("")}
          <div class="phase-legend__row"><i class="is-hatch"></i><span>${t("screen1.table.no_data")}</span><em class="num">${bundle.no_return}</em></div>
        </div>
      </div>
      <p class="chart-caption">${t("screen_impl.map.caption")}</p>
    </section>


    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("grid", t("screen_impl.grid.title"))}</div>
      <p class="chart-caption">${t("screen_impl.grid.caption")}</p>
      <ol class="phase-track" id="phase-legend"></ol>
      <div class="chart-legend">
        <span class="chart-legend__item">${renderStatus("met", t("status.met"))}</span>
        <span class="chart-legend__item">${renderStatus("partly_met", t("status.partly_met"))}</span>
        <span class="chart-legend__item">${renderStatus("not_met", t("status.not_met"))}</span>
        <span class="chart-legend__item">${renderStatus("not_reported", t("status.not_reported"))}</span>
      </div>
      <div class="toolbar"><button type="button" class="btn" id="export-btn">${t("common.export_csv")}</button></div>
      <div id="implementation-table"></div>
    </section>
  `;

  // ---- map of phases (follows the key figures; never the first element)
  const phaseOf = new Map(countries.map((c) => [c.iso3, c.phase]));
  const phaseMap = renderPhaseMap(
    geo,
    phaseOf,
    (iso3) => countryName(iso3, countries.find((c) => c.iso3 === iso3)?.name ?? iso3),
    {
      phase: (n) => `${t("screen_impl.phase_n", { n })} · ${t(`screen3.phase_name.${n}`)}`,
      none: t("screen1.table.no_data"),
    },
  );
  if (phaseMap) container.querySelector("#phase-map")!.appendChild(phaseMap);

  // ---- phase/step legend, above the detail table so a reader meets it
  // before the grid rather than after scrolling past it
  const legend = container.querySelector("#phase-legend")!;
  const phaseNos = [...new Set(stepDim.map((s) => s.phase_no))].sort((a, b) => a - b);
  for (const phaseNo of phaseNos) {
    const phaseName = phaseLabel(phaseNo, stepDim.find((s) => s.phase_no === phaseNo)!.phase_label);
    const stepsOfPhase = stepDim.filter((s) => s.phase_no === phaseNo);
    const li = document.createElement("li");
    li.className = "phase-track__phase";
    li.innerHTML = `<span class="phase-track__no num">${phaseNo}</span>
      <h4></h4>
      <ol class="phase-track__steps">${stepsOfPhase
        .map((s) => `<li><b class="num">${s.step_no}</b><span></span></li>`)
        .join("")}</ol>`;
    // labels come from the bundle; set as text, never parsed as markup
    li.querySelector("h4")!.textContent = phaseName;
    li.querySelectorAll(".phase-track__steps span").forEach((el, i) => {
      el.textContent = stepLabel(stepsOfPhase[i]?.step_no ?? 0, stepsOfPhase[i]?.step_label ?? "");
    });
    legend.append(li);
  }

  // Columns for CSV export only -- the visual table is components/phase-grid.ts,
  // built directly from stepDim/countries, not from this Column[] list.
  const csvColumns: Column<ImplementationCountry>[] = [
    { key: "name", label: t("common.select_country"), render: (c) => c.name },
    { key: "phase", label: t("screen_impl.column.phase"), render: (c) => phaseShort(c.phase) },
    {
      key: "workbook_phase",
      label: t("screen_impl.column.workbook_phase"),
      render: (c) => (c.workbook_phase === null ? "NR" : String(c.workbook_phase)),
    },
    {
      key: "agreement",
      label: t("screen_impl.column.agreement"),
      render: (c) => (c.agreement === null ? "NR" : t(`screen_impl.agreement.${c.agreement}`)),
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
  tableHost.appendChild(buildPhaseGrid(t("screen_impl.grid.title"), stepDim, sorted));

  container.querySelector("#export-btn")!.addEventListener("click", () => {
    const { headers, rows } = tableToCSVData<ImplementationCountry>(csvColumns, sorted);
    downloadCSV("implementation_phases", headers, rows);
  });
}
