import { getFacilities } from "@/lib/bundle";
import { fmtCount } from "@/lib/format";
import { t } from "@/lib/i18n";
import { buildPaginatedTable, tableToCSVData, type Column } from "@/components/table";
import { downloadCSV } from "@/components/csv";
import { panelTitleWithIcon, renderKpiCard, renderKpiRow } from "@/components/kpi";
import { renderSourceRef } from "@/components/provenance";
import { renderRegisterStatus } from "@/screens/country-profile";
import { loadWhoGeo, renderFacilityMap, STATUSES } from "@/components/facility-map";
import type { FacilityRow } from "@/lib/types";

/**
 * Screen 5: "Where are the sites and what state are they in?" KPI row, then
 * the facility map (CLAUDE.md: never a map as the first element), then the
 * register. The map draws WHO GIS Centre boundaries (components/facility-map.ts);
 * every point carries its source (data/reference/facility_coordinates.csv).
 */
export async function renderFacilities(container: HTMLElement): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const bundle = await getFacilities();
  const k = bundle.kpis;
  const rows = bundle.rows;

  container.innerHTML = `
    <header class="page-head">
      <h2 class="screen-title">${t("screen5.title")}</h2>
      <p class="panel__question">${t("screen5.question")}</p>
    </header>

    ${renderKpiRow([
      renderKpiCard("facility", fmtCount(k.total), t("screen5.kpi.total")),
      renderKpiCard("pulse", fmtCount(k.active), t("screen5.kpi.active")),
      renderKpiCard("country", fmtCount(k.countries), t("screen5.kpi.countries")),
      renderKpiCard(
        "map",
        t("common.n_of_total", { n: k.mapped, total: k.total }),
        t("screen5.kpi.mapped_v2", { approx: k.approximate }),
      ),
    ])}

    <p class="exec-message">${t("screen5.summary", {
      total: fmtCount(k.total),
      countries: k.countries,
      active: fmtCount(k.active),
      planned: k.by_status.planned ?? 0,
      names: k.names_to_confirm,
    })}</p>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("map", t("screen5.map.title"))}</div>
      <div id="facility-map" class="facility-map"></div>
      <p class="chart-caption">${t("screen5.map.caption_v2", { mapped: k.mapped, approx: k.approximate, total: k.total, off: k.location_to_confirm })}</p>
      <p class="map-disclaimer">${t("screen5.map.disclaimer")}</p>
    </section>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("facility", t("screen5.register.title"))}</div>
      <div class="screen-controls">
        <label>${t("common.select_country")}
          <select id="country-filter"><option value="">${t("common.all_countries")}</option></select>
        </label>
        <label>${t("table.status")}
          <select id="status-filter">
            <option value="">${t("common.all")}</option>
            ${STATUSES.map((s) => `<option value="${s}">${t(`register_status.${s}`)}</option>`).join("")}
          </select>
        </label>
        <button type="button" class="btn" id="export-btn">${t("common.export_csv")}</button>
      </div>
      <div id="facility-table"></div>
      <p class="chart-caption">${t("screen5.register.caption")}</p>
    </section>

    <section class="panel">
      <div class="panel__header">${panelTitleWithIcon("alert", t("screen5.to_confirm.title"))}</div>
      <p class="chart-caption">${t("screen5.to_confirm.caption")}</p>
      <div id="to-confirm" class="pill-list"></div>
    </section>
  `;

  // ---- country filters (both lists in alphabetical order)
  const countries = [...new Map(rows.map((f) => [f.iso3, f.country])).entries()].sort((a, b) =>
    a[1].localeCompare(b[1]),
  );
  for (const id of ["#country-filter"]) {
    const sel = container.querySelector<HTMLSelectElement>(id)!;
    for (const [iso3, name] of countries) {
      const opt = document.createElement("option");
      opt.value = iso3;
      opt.textContent = name;
      sel.appendChild(opt);
    }
  }

  // ---- map: WHO GIS Centre boundaries, loaded only on this screen
  const geo = await loadWhoGeo();
  renderFacilityMap(container.querySelector<HTMLElement>("#facility-map")!, bundle, geo);

  // ---- register
  const columns: Column<FacilityRow>[] = [
    {
      key: "name",
      label: t("table.facility"),
      html: true,
      render: (f) =>
        `${f.name ?? f.facility_id}${f.name_status === "to_confirm" ? ` <small class="muted">${t("screen5.name_to_confirm")}</small>` : ""}`,
      csv: (f) => f.name ?? f.facility_id,
    },
    { key: "country", label: t("common.select_country"), render: (f) => f.country },
    {
      key: "district",
      label: t("table.district"),
      render: (f) => [f.district, f.region].filter(Boolean).join(", ") || "NR",
    },
    { key: "partner", label: t("table.partner"), render: (f) => f.partner ?? "NR" },
    {
      key: "status",
      label: t("table.status"),
      html: true,
      render: renderRegisterStatus,
      csv: (f) => f.register_status ?? "",
    },
    { key: "conditions", label: t("table.conditions"), render: (f) => f.conditions ?? "NR" },
    { key: "patients", label: t("table.patients_reported"), render: (f) => f.patients_reported ?? "NR" },
    {
      key: "source",
      label: t("common.source_slide"),
      html: true,
      render: (f) => renderSourceRef(f.source_ref) || "NR",
      csv: (f) => f.source_ref ?? "",
    },
    {
      key: "location",
      label: t("table.location"),
      render: (f) =>
        f.mapped
          ? t("screen5.location.on_map")
          : f.approximate
            ? t("screen5.location.approximate")
            : t("screen5.location.to_confirm"),
    },
  ];
  const tableHost = container.querySelector("#facility-table")!;
  const countryFilter = container.querySelector<HTMLSelectElement>("#country-filter")!;
  const statusFilter = container.querySelector<HTMLSelectElement>("#status-filter")!;
  const filtered = () =>
    rows.filter(
      (f) =>
        (!countryFilter.value || f.iso3 === countryFilter.value) &&
        (!statusFilter.value || f.register_status === statusFilter.value),
    );
  const drawTable = () =>
    tableHost.replaceChildren(buildPaginatedTable(t("screen5.register.title"), columns, filtered(), 25));
  countryFilter.addEventListener("change", drawTable);
  statusFilter.addEventListener("change", drawTable);
  drawTable();
  container.querySelector("#export-btn")!.addEventListener("click", () => {
    const { headers, rows: csvRows } = tableToCSVData(columns, filtered());
    downloadCSV("facility_register", headers, csvRows);
  });

  // ---- location to confirm: every facility not on the map, never dropped
  container.querySelector("#to-confirm")!.innerHTML = rows
    .filter((f) => !f.mapped && !f.approximate)
    .map(
      (f) =>
        `<span class="pill" title="${(f.note ?? "").replace(/"/g, "&quot;")}">${f.name ?? f.facility_id} <small>${f.iso3}</small></span>`,
    )
    .join("");
}
