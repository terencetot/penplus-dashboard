import { getFacilities, getOverview } from "@/lib/bundle";
import { fmtCount, fmtDate, NR } from "@/lib/format";
import { t } from "@/lib/i18n";
import { isDemoMode } from "@/lib/demo";
import { buildPaginatedTable, tableToCSVData, type Column } from "@/components/table";
import { downloadCSV } from "@/components/csv";
import { renderKpiCard, renderKpiRow } from "@/components/kpi";
import { renderStatus, statusFromReadiness } from "@/lib/status";
import { facilityStatusKey, projectSupportedKey, readinessKey } from "@/lib/vocab";
import type { FacilityRow, FacilityStatus } from "@/lib/types";

const FACILITY_STATUSES: FacilityStatus[] = [
  "operational",
  "started_this_period",
  "under_preparation",
  "suspended",
  "closed",
];

export async function renderFacilities(container: HTMLElement): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const [facilities, overview] = await Promise.all([getFacilities(), getOverview()]);
  const nameByIso3 = new Map(overview.countries.map((c) => [c.iso3, c.name]));

  const operationalCount = facilities.rows.filter(
    (f) => f.status === "operational" || f.status === "started_this_period",
  ).length;
  // avg_quality_score is computed once in export.py, not re-derived here
  // (CLAUDE.md rule 1: no arithmetic in the front end).
  const avgQuality = facilities.avg_quality_score;
  const countriesWithFacilities = new Set(facilities.rows.map((f) => f.iso3)).size;

  container.innerHTML = `
    <h2 class="screen-title">${t("screen5.title")}</h2>
    <p class="panel__question">${t("screen5.question")}</p>

    ${renderKpiRow([
      renderKpiCard("facility", fmtCount(facilities.rows.length), t("screen5.kpi.total")),
      renderKpiCard("pulse", fmtCount(operationalCount), t("screen5.kpi.operational")),
      renderKpiCard(
        "shield",
        avgQuality === null ? NR : `${avgQuality}%`,
        t("screen5.kpi.avg_quality"),
        avgQuality === null,
      ),
      renderKpiCard("country", fmtCount(countriesWithFacilities), t("screen5.kpi.countries")),
    ])}

    <p class="exec-message">${t("screen5.summary", {
      total: fmtCount(facilities.rows.length),
      countries: countriesWithFacilities,
      operational: fmtCount(operationalCount),
    })}</p>

    <section class="panel">
      <div class="screen-controls">
        <label>${t("common.select_country")}
          <select id="country-filter"><option value="">${t("common.all_countries")}</option></select>
        </label>
        <label>${t("table.status")}
          <select id="status-filter">
            <option value="">${t("common.all")}</option>
            ${FACILITY_STATUSES.map((s) => `<option value="${s}">${t(facilityStatusKey(s))}</option>`).join("")}
          </select>
        </label>
        <div class="toolbar"><button type="button" class="btn" id="export-btn">${t("common.export_csv")}</button></div>
      </div>

      <div id="facility-table"></div>
      <p class="chart-caption">${t(isDemoMode() ? "screen5.table.caption_demo" : "screen5.table.caption")}</p>
    </section>
  `;

  const countrySelect = container.querySelector<HTMLSelectElement>("#country-filter")!;
  for (const c of [...overview.countries].sort((a, b) => a.name.localeCompare(b.name))) {
    if (!facilities.rows.some((f) => f.iso3 === c.iso3)) continue;
    const opt = document.createElement("option");
    opt.value = c.iso3;
    opt.textContent = c.name;
    countrySelect.appendChild(opt);
  }
  const statusSelect = container.querySelector<HTMLSelectElement>("#status-filter")!;

  const columns: Column<FacilityRow>[] = [
    { key: "name", label: t("table.facility"), render: (f) => f.name },
    { key: "iso3", label: t("common.select_country"), render: (f) => nameByIso3.get(f.iso3) ?? f.iso3 },
    { key: "district", label: t("table.district"), render: (f) => f.district ?? NR },
    {
      key: "status",
      label: t("table.status"),
      render: (f) => (f.status ? t(facilityStatusKey(f.status)) : NR),
    },
    {
      key: "project_supported",
      label: t("table.project_supported"),
      render: (f) => (f.project_supported ? t(projectSupportedKey(f.project_supported)) : NR),
    },
    {
      key: "readiness_class",
      label: t("table.readiness"),
      html: true,
      render: (f) => {
        if (!f.readiness_class) return NR;
        const status = statusFromReadiness(f.readiness_class);
        return renderStatus(status, t(readinessKey(f.readiness_class)));
      },
      csv: (f) => (f.readiness_class ? t(readinessKey(f.readiness_class)) : NR),
    },
    {
      key: "quality_score",
      label: t("table.quality_score"),
      numeric: true,
      render: (f) => (f.quality_score === null ? NR : `${f.quality_score}%`),
      csv: (f) => (f.quality_score === null ? NR : String(f.quality_score)),
    },
    {
      key: "active_end",
      label: t("table.active_in_care"),
      numeric: true,
      render: (f) => fmtCount(f.active_end),
    },
    { key: "last_seen", label: t("common.as_of"), render: (f) => fmtDate(f.last_seen) },
  ];

  let currentRows: FacilityRow[] = facilities.rows;

  function apply() {
    const iso3 = countrySelect.value;
    const status = statusSelect.value;
    currentRows = facilities.rows.filter(
      (f) => (!iso3 || f.iso3 === iso3) && (!status || f.status === status),
    );
    container
      .querySelector("#facility-table")!
      .replaceChildren(buildPaginatedTable(t("screen5.title"), columns, currentRows));
  }
  countrySelect.addEventListener("change", apply);
  statusSelect.addEventListener("change", apply);
  apply();

  container.querySelector("#export-btn")!.addEventListener("click", () => {
    const { headers, rows } = tableToCSVData<FacilityRow>(
      columns.map((c) => ({ ...c, csv: c.csv ?? c.render })),
      currentRows,
    );
    downloadCSV("facilities", headers, rows);
  });
}
