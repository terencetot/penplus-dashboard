import * as Plot from "@observablehq/plot";
import { t } from "@/lib/i18n";
import { emptyChart } from "@/charts/empty";
import type { FacilitiesBundle, FacilityRow, RegisterStatus } from "@/lib/types";

/** WHO GIS Centre boundaries, as written by the map-asset build (who_africa.json). */
export interface WhoGeo {
  source: string;
  countries: { type: "FeatureCollection"; features: CountryFeature[] };
  disputed_borders: { type: "FeatureCollection"; features: unknown[] };
  disputed_areas: { type: "FeatureCollection"; features: unknown[] };
}
interface CountryFeature {
  type: "Feature";
  properties: {
    iso3: string;
    name: string;
    region: string;
    cohort: "phase_1" | "phase_2" | null;
    lon: number;
    lat: number;
  };
  geometry: unknown;
}

export const STATUSES: RegisterStatus[] = ["active", "partial", "planned", "to_confirm"];
/** Shape by status, never size or colour by performance (design brief). */
export const SYMBOL: Record<RegisterStatus, string> = {
  active: "circle",
  partial: "diamond",
  planned: "triangle",
  to_confirm: "square",
};

const OCEAN = "#e8eff8";
const LAND_OTHER = "#f6f7f9";
const LAND_ROUND1 = "#d5e0f1";
const LAND_ROUND2 = "#e9eef7";
const LAND_SELECTED = "#b7c9e6";
const POINT = "#0e2a63";
/** The region frame, fixed: every PEN-Plus facility sits inside it. */
const REGION_FRAME = {
  type: "MultiPoint",
  coordinates: [
    [-18.5, -27],
    [45, 16.5],
  ],
};

/** WHO's upper-case names, title-cased by the asset build, with the small words lowered. */
function displayName(name: string): string {
  return name.replace(/ (Of|The|And|De|Du|La)(?= )/g, (w) => w.toLowerCase());
}

export function loadWhoGeo(): Promise<WhoGeo | null> {
  return fetch(`${import.meta.env.BASE_URL}assets/geo/who_africa.json`)
    .then((r) => (r.ok ? (r.json() as Promise<WhoGeo>) : null))
    .catch(() => null);
}

/**
 * The facility map: WHO GIS Centre country boundaries (thin white lines,
 * disputed borders dashed and disputed areas grey, as WHO maps draw them),
 * PEN-Plus countries tinted by funding round, and one point per facility.
 * Solid: the facility's own coordinates. Hollow: an approximate town point.
 * Choosing a country frames its WHO outline and labels every facility.
 */
export function renderFacilityMap(
  host: HTMLElement,
  bundle: FacilitiesBundle,
  geo: WhoGeo | null,
): { select: (iso3: string) => void } {
  host.innerHTML = `<div class="map-layout">
      <div class="map-stage">
        <div class="map-stage__head">
          <span class="map-stage__title" id="map-title">${t("screen5.map.all")}</span>
          <button type="button" class="btn btn--ghost" id="map-reset" hidden>${t("screen5.map.back")}</button>
        </div>
        <div class="map-canvas" id="map-canvas"></div>
      </div>
      <aside class="map-side" aria-label="${t("screen5.map.by_country")}">
        <h4>${t("screen5.map.by_country")}</h4>
        <ul class="map-countries" id="map-countries">${bundle.by_country
          .map(
            (c) => `<li><button type="button" data-iso3="${c.iso3}">
              <span class="map-countries__name">${c.country}</span>
              <span class="map-countries__n num">${c.total}</span>
            </button></li>`,
          )
          .join("")}</ul>
        <div class="map-legend">
          ${STATUSES.map(
            (s) => `<span><i class="sym sym--${SYMBOL[s]}"></i>${t(`register_status.${s}`)}</span>`,
          ).join("")}
          <span><i class="sym sym--hollow"></i>${t("screen5.map.approximate")}</span>
          <span><i class="swatch" style="background:${LAND_ROUND1}"></i>${t("common.phase1")}</span>
          <span><i class="swatch swatch--r2" style="background:${LAND_ROUND2}"></i>${t("common.phase2")}</span>
          <span><i class="dash"></i>${t("screen5.map.disputed")}</span>
        </div>
      </aside>
    </div>`;

  const canvas = host.querySelector<HTMLElement>("#map-canvas")!;
  const title = host.querySelector<HTMLElement>("#map-title")!;
  const reset = host.querySelector<HTMLButtonElement>("#map-reset")!;
  const buttons = Array.from(host.querySelectorAll<HTMLButtonElement>("#map-countries button"));
  const nameOf = new Map(bundle.by_country.map((c) => [c.iso3, c.country]));

  const draw = (iso3: string) => {
    const points = bundle.rows.filter((f) => (f.mapped || f.approximate) && (!iso3 || f.iso3 === iso3));
    const selected = iso3 ? geo?.countries.features.find((f) => f.properties.iso3 === iso3) : undefined;
    try {
      canvas.replaceChildren(plotMap(points, geo, iso3, selected));
    } catch (err) {
      // a damaged boundary file must never take the screen down: points only
      console.error(err);
      canvas.replaceChildren(plotMap(points, null, iso3, undefined));
    }
    title.textContent = iso3 ? (nameOf.get(iso3) ?? iso3) : t("screen5.map.all");
    reset.hidden = !iso3;
    for (const b of buttons) b.classList.toggle("is-active", b.dataset.iso3 === iso3);
  };
  for (const b of buttons) b.addEventListener("click", () => draw(b.dataset.iso3 ?? ""));
  reset.addEventListener("click", () => draw(""));
  draw("");
  return { select: draw };
}

function plotMap(
  points: FacilityRow[],
  geo: WhoGeo | null,
  iso3: string,
  selected: CountryFeature | undefined,
): SVGElement | HTMLElement {
  if (!geo && points.length === 0) return emptyChart(220, t("screen5.map.empty"));
  const zoomed = Boolean(iso3);
  const countries = geo?.countries.features ?? [];
  const fillOf = (f: CountryFeature) =>
    f.properties.iso3 === iso3
      ? LAND_SELECTED
      : f.properties.cohort === "phase_1"
        ? LAND_ROUND1
        : f.properties.cohort === "phase_2"
          ? LAND_ROUND2
          : LAND_OTHER;
  const tip = {
    Facility: (f: FacilityRow) => f.name ?? f.facility_id,
    Country: "country",
    District: (f: FacilityRow) => [f.district ?? f.town, f.region].filter(Boolean).join(", "),
    Partner: (f: FacilityRow) => f.partner ?? "",
    Status: (f: FacilityRow) => t(`register_status.${f.register_status ?? "to_confirm"}`),
    Conditions: (f: FacilityRow) => f.conditions ?? "",
    Patients: (f: FacilityRow) => f.patients_reported ?? "",
    Location: (f: FacilityRow) =>
      f.approximate ? t("screen5.location.approximate") : t("screen5.location.on_map"),
  };
  const exact = points.filter((p) => p.mapped);
  const approx = points.filter((p) => p.approximate);
  // PEN-Plus country names, region view only; facility names, country view only
  const labelled = zoomed
    ? []
    : countries.filter((f) => f.properties.cohort !== null && f.properties.region === "AFRO");

  return Plot.plot({
    width: 1000,
    height: zoomed ? 680 : 780,
    margin: 0,
    projection: {
      type: "mercator",
      domain: (selected ?? REGION_FRAME) as never,
      inset: zoomed ? 40 : 6,
    },
    style: { fontFamily: "var(--font-family)", fontSize: "12px", background: OCEAN },
    symbol: { domain: STATUSES, range: STATUSES.map((s) => SYMBOL[s]) },
    marks: [
      Plot.geo(countries, {
        fill: fillOf,
        stroke: "#ffffff",
        strokeWidth: zoomed ? 1.4 : 0.9,
      }),
      geo ? Plot.geo(geo.disputed_areas.features, { fill: "#d9dde3", stroke: "none" }) : null,
      geo
        ? Plot.geo(geo.disputed_borders.features, {
            stroke: "#9aa5b8",
            strokeWidth: 1,
            strokeDasharray: "3,3",
          })
        : null,
      Plot.text(labelled, {
        x: (f: CountryFeature) => f.properties.lon,
        y: (f: CountryFeature) => f.properties.lat,
        text: (f: CountryFeature) => displayName(f.properties.name),
        fontSize: 9.5,
        fontWeight: 600,
        fill: "#5d6b85",
        stroke: "#ffffff",
        strokeOpacity: 0.7,
        strokeWidth: 2.5,
        paintOrder: "stroke",
        lineWidth: 8,
      }),
      Plot.dot(approx, {
        x: "longitude",
        y: "latitude",
        symbol: "register_status",
        r: zoomed ? 8 : 6,
        fill: "#ffffff",
        stroke: POINT,
        strokeWidth: 1.8,
        channels: tip,
        tip: { format: { x: false, y: false, symbol: false } },
      }),
      Plot.dot(exact, {
        x: "longitude",
        y: "latitude",
        symbol: "register_status",
        r: zoomed ? 8.5 : 6.5,
        fill: POINT,
        stroke: "#ffffff",
        strokeWidth: 2,
        channels: tip,
        tip: { format: { x: false, y: false, symbol: false } },
      }),
      zoomed
        ? Plot.text(points, {
            x: "longitude",
            y: "latitude",
            text: (f: FacilityRow) => f.name ?? f.facility_id,
            dx: 13,
            textAnchor: "start",
            fontSize: 12.5,
            fontWeight: 600,
            fill: "#0b1a3a",
            stroke: "#ffffff",
            strokeWidth: 4,
            paintOrder: "stroke",
            lineWidth: 18,
          })
        : null,
    ],
  });
}
