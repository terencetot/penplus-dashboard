import { getFacilities, getOverview } from "@/lib/bundle";
import { fmtCount, fmtDate, NR } from "@/lib/format";
import { t } from "@/lib/i18n";
import { buildTable, tableToCSVData, type Column } from "@/components/table";
import { downloadCSV } from "@/components/csv";
import type { FacilityRow } from "@/lib/types";

const READINESS_LABEL: Record<string, string> = {
  green: "Green",
  amber: "Amber",
  red: "Red",
  not_assessed: "Not assessed",
};

export async function renderFacilities(container: HTMLElement): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const [facilities, overview] = await Promise.all([getFacilities(), getOverview()]);
  const nameByIso3 = new Map(overview.countries.map((c) => [c.iso3, c.name]));

  container.innerHTML = `
    <h2>${t("screen5.title")}</h2>
    <p class="panel__question">${t("screen5.question")}</p>
    <p class="callout">${t("screen5.table.caption")}</p>

    <div class="screen-controls">
      <label>${t("common.select_country")}
        <select id="country-filter"><option value="">${t("common.all_countries")}</option></select>
      </label>
      <label>Status
        <select id="status-filter">
          <option value="">${t("common.all_countries")}</option>
          <option value="operational">Operational</option>
          <option value="started_this_period">Started this period</option>
          <option value="under_preparation">Under preparation</option>
          <option value="suspended">Suspended</option>
          <option value="closed">Closed</option>
        </select>
      </label>
      <div class="toolbar"><button type="button" class="btn" id="export-btn">${t("common.export_csv")}</button></div>
    </div>

    <div id="facility-table"></div>
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
    { key: "name", label: "Facility", render: (f) => f.name },
    { key: "iso3", label: t("common.select_country"), render: (f) => nameByIso3.get(f.iso3) ?? f.iso3 },
    { key: "district", label: "District", render: (f) => f.district ?? NR },
    { key: "status", label: "Status", render: (f) => f.status ?? NR },
    { key: "project_supported", label: "Project-supported", render: (f) => f.project_supported ?? NR },
    {
      key: "readiness_class",
      label: "Readiness",
      render: (f) => (f.readiness_class ? (READINESS_LABEL[f.readiness_class] ?? f.readiness_class) : NR),
    },
    {
      key: "quality_score",
      label: "Quality score",
      numeric: true,
      render: (f) => (f.quality_score === null ? NR : String(f.quality_score)),
    },
    { key: "active_end", label: "Active in care", numeric: true, render: (f) => fmtCount(f.active_end) },
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
      .replaceChildren(buildTable(t("screen5.title"), columns, currentRows));
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
