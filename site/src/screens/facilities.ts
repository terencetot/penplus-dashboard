import * as Plot from "@observablehq/plot";
import { getFacilities } from "@/lib/bundle";
import { fmtCount } from "@/lib/format";
import { t } from "@/lib/i18n";
import { buildPaginatedTable, tableToCSVData, type Column } from "@/components/table";
import { downloadCSV } from "@/components/csv";
import { panelTitleWithIcon, renderKpiCard, renderKpiRow } from "@/components/kpi";
import { renderSourceRef } from "@/components/provenance";
import { renderRegisterStatus } from "@/screens/country-profile";
import { emptyChart } from "@/charts/empty";
import type { FacilityRow, RegisterStatus } from "@/lib/types";

const STATUSES: RegisterStatus[] = ["active", "partial", "planned", "to_confirm"];
/** Shape by status, never size or colour by performance (design brief). */
const SYMBOL: Record<RegisterStatus, string> = {
  active: "circle",
  partial: "diamond",
  planned: "triangle",
  to_confirm: "square",
};

/**
 * Screen 5: "Where are the sites and what state are they in?" KPI row, then
 * the facility map (CLAUDE.md: never a map as the first element), then the
 * register. Points come only from coordinates that passed every rule of
 * GEOCODING_PROTOCOL.md or were checked by a person; everything else is
 * listed as "location to confirm". No boundaries are drawn: WHO-cleared
 * boundary files are not part of this build.
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
      renderKpiCard("map", t("common.n_of_total", { n: k.mapped, total: k.total }), t("screen5.kpi.mapped")),
    ])}

    <p class="exec-message">${t("screen5.summary", {
      total: fmtCount(k.total),
      countries: k.countries,
      active: fmtCount(k.active),
      planned: k.by_status.planned ?? 0,
      names: k.names_to_confirm,
    })}</p>

    <section class="panel">
      <div class="panel__header">
        ${panelTitleWithIcon("map", t("screen5.map.title"))}
        <label class="inline-filter">${t("common.select_country")}
          <select id="map-country"><option value="">${t("common.all_countries")}</option></select>
        </label>
      </div>
      <div id="facility-map" class="facility-map"></div>
      <div class="chart-legend" id="map-legend"></div>
      <p class="chart-caption">${t("screen5.map.caption", { mapped: k.mapped, total: k.total })}</p>
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
  for (const id of ["#map-country", "#country-filter"]) {
    const sel = container.querySelector<HTMLSelectElement>(id)!;
    for (const [iso3, name] of countries) {
      const opt = document.createElement("option");
      opt.value = iso3;
      opt.textContent = name;
      sel.appendChild(opt);
    }
  }

  // ---- map
  const mapHost = container.querySelector<HTMLElement>("#facility-map")!;
  const mapSelect = container.querySelector<HTMLSelectElement>("#map-country")!;
  container.querySelector("#map-legend")!.innerHTML = STATUSES.map(
    (s) =>
      `<span class="chart-legend__item"><span class="sym sym--${SYMBOL[s]}"></span>${t(`register_status.${s}`)}</span>`,
  ).join("");
  const drawMap = () => {
    const iso3 = mapSelect.value;
    const points = rows.filter((f) => f.mapped && (!iso3 || f.iso3 === iso3));
    mapHost.replaceChildren(facilityMap(points, iso3 !== ""));
  };
  mapSelect.addEventListener("change", drawMap);
  drawMap();

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
          : f.geo_precision === "town"
            ? t("screen5.location.town_only")
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
    .filter((f) => !f.mapped)
    .map(
      (f) =>
        `<span class="pill" title="${(f.note ?? "").replace(/"/g, "&quot;")}">${f.name ?? f.facility_id} <small>${f.iso3}</small></span>`,
    )
    .join("");
}

/** Points on a plain longitude / latitude frame with a graticule. */
function facilityMap(points: FacilityRow[], zoomed: boolean): SVGElement | HTMLElement {
  if (points.length === 0) return emptyChart(220, t("screen5.map.empty"));
  const lons = points.map((p) => p.longitude!);
  const lats = points.map((p) => p.latitude!);
  // display extent only (a frame for the drawing, not a published figure)
  const pad = zoomed ? 1.5 : 4;
  const domain = zoomed
    ? [
        [Math.min(...lons) - pad, Math.min(...lats) - pad],
        [Math.max(...lons) + pad, Math.max(...lats) + pad],
      ]
    : [
        [-18, -35],
        [52, 20],
      ];
  return Plot.plot({
    width: 1100,
    height: zoomed ? 420 : 560,
    projection: {
      type: "equirectangular",
      domain: { type: "MultiPoint", coordinates: domain },
      inset: 10,
    },
    style: { fontFamily: "var(--font-family)", fontSize: "12px", background: "transparent" },
    symbol: { domain: STATUSES, range: STATUSES.map((s) => SYMBOL[s]) },
    marks: [
      Plot.graticule({ stroke: "var(--line)", strokeOpacity: 1 }),
      Plot.dot(points, {
        x: "longitude",
        y: "latitude",
        symbol: "register_status",
        r: 7,
        fill: "var(--navy-700)",
        stroke: "#fff",
        strokeWidth: 1.5,
        channels: {
          Facility: (f: FacilityRow) => f.name ?? f.facility_id,
          Country: "country",
          District: (f: FacilityRow) => f.district ?? f.town ?? "",
          Partner: (f: FacilityRow) => f.partner ?? "",
          Status: (f: FacilityRow) => t(`register_status.${f.register_status ?? "to_confirm"}`),
          Conditions: (f: FacilityRow) => f.conditions ?? "",
          Patients: (f: FacilityRow) => f.patients_reported ?? "",
          Source: (f: FacilityRow) => f.source_ref ?? "",
        },
        tip: {
          format: { x: false, y: false, symbol: false },
        },
      }),
      Plot.text(points, {
        x: "longitude",
        y: "latitude",
        text: (f: FacilityRow) => f.name ?? f.facility_id,
        dy: -13,
        fontSize: 10.5,
        fill: "var(--ink)",
        stroke: "#fff",
        strokeWidth: 3,
        paintOrder: "stroke",
      }),
    ],
  });
}
