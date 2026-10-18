import * as Plot from "@observablehq/plot";
import { t } from "@/lib/i18n";
import { navigate } from "@/router";
import { emptyChart } from "@/charts/empty";
import { renderSourceRef } from "@/components/provenance";
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

/* Atlas palette: the navy of the hero band. Cohort is carried by tint and
   by the legend's words; points are white so they read on every tint. */
const LAND_OTHER = "rgba(255,255,255,0.045)";
const LAND_ROUND1 = "#24488f";
const LAND_ROUND2 = "#16316b";
const LAND_SELECTED = "#3f67b5";
const BORDER = "rgba(255,255,255,0.22)";
const POINT = "#ffffff";
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
 * The facility atlas: WHO GIS Centre boundaries (disputed borders dashed,
 * disputed areas shaded, as WHO maps draw them), PEN-Plus countries tinted by
 * HCT round, one point per facility -- solid at the facility's own
 * coordinates, hollow at an approximate town point, shape by status. A click
 * on a point opens its card; a country in the side list frames its WHO
 * outline and names every facility. Every figure shown comes from export.py.
 */
export function renderFacilityMap(
  host: HTMLElement,
  bundle: FacilitiesBundle,
  geo: WhoGeo | null,
): { select: (iso3: string) => void } {
  const k = bundle.kpis;
  host.innerHTML = `<div class="atlas">
      <div class="atlas__stage">
        <div class="atlas__top">
          <div>
            <span class="atlas__eyebrow">${t("screen5.map.eyebrow")}</span>
            <h4 class="atlas__title" id="map-title">${t("screen5.map.all")}</h4>
          </div>
          <button type="button" class="atlas__back" id="map-reset" hidden>← ${t("screen5.map.back")}</button>
        </div>
        <div class="atlas__stats">
          <div><b class="num">${k.mapped}</b><span>${t("screen5.map.stat_located")}</span></div>
          <div><b class="num">${k.approximate}</b><span>${t("screen5.map.stat_approx")}</span></div>
          <div><b class="num">${k.countries}</b><span>${t("screen5.map.stat_countries")}</span></div>
        </div>
        <div class="atlas__canvas" id="map-canvas"></div>
        <div class="atlas__card" id="map-card" hidden></div>
        <div class="atlas__legend">
          ${STATUSES.map((s) => `<span><i class="sym sym--${SYMBOL[s]}"></i>${t(`register_status.${s}`)}</span>`).join("")}
          <span><i class="sym sym--hollow"></i>${t("screen5.map.approximate_short")}</span>
          <span><i class="swatch" style="background:${LAND_ROUND1}"></i>${t("common.phase1")}</span>
          <span><i class="swatch" style="background:${LAND_ROUND2}"></i>${t("common.phase2")}</span>
          <span><i class="dash"></i>${t("screen5.map.disputed")}</span>
        </div>
      </div>
      <aside class="atlas__side" aria-label="${t("screen5.map.by_country")}">
        <h4>${t("screen5.map.by_country")}</h4>
        <ul class="atlas__countries" id="map-countries">${bundle.by_country
          .map(
            (c) => `<li><button type="button" data-iso3="${c.iso3}">
              <span class="atlas__cname">${c.country}</span>
              <span class="atlas__cn num">${c.total}</span>
              <span class="atlas__bar" aria-hidden="true">
                <i class="is-exact" style="flex-grow:${c.mapped}"></i><i class="is-approx" style="flex-grow:${c.approximate}"></i><i class="is-off" style="flex-grow:${c.off_map}"></i>
              </span>
            </button></li>`,
          )
          .join("")}</ul>
        <p class="atlas__sidenote"><i class="is-exact"></i>${t("screen5.map.bar_exact")} <i class="is-approx"></i>${t("screen5.map.bar_approx")} <i class="is-off"></i>${t("screen5.map.bar_off")}</p>
      </aside>
    </div>`;

  const canvas = host.querySelector<HTMLElement>("#map-canvas")!;
  const card = host.querySelector<HTMLElement>("#map-card")!;
  const title = host.querySelector<HTMLElement>("#map-title")!;
  const reset = host.querySelector<HTMLButtonElement>("#map-reset")!;
  const stats = host.querySelector<HTMLElement>(".atlas__stats")!;
  const buttons = Array.from(host.querySelectorAll<HTMLButtonElement>("#map-countries button"));
  const nameOf = new Map(bundle.by_country.map((c) => [c.iso3, c.country]));

  const showCard = (f: FacilityRow) => {
    card.hidden = false;
    card.innerHTML = `<button type="button" class="atlas__close" aria-label="${t("common.close")}">×</button>
      <span class="atlas__card-country">${f.country}</span>
      <h5>${f.name ?? f.facility_id}</h5>
      <div class="atlas__card-chips">
        <span class="reg reg--${f.register_status ?? "to_confirm"}">${t(`register_status.${f.register_status ?? "to_confirm"}`)}</span>
        <span class="atlas__loc${f.approximate ? " is-approx" : ""}">${f.approximate ? t("screen5.location.approximate") : t("screen5.location.on_map")}</span>
      </div>
      <dl>
        ${row(t("table.district"), [f.district ?? f.town, f.region].filter(Boolean).join(", "))}
        ${row(t("table.partner"), f.partner)}
        ${row(t("table.conditions"), f.conditions)}
        ${row(t("table.patients_reported"), f.patients_reported)}
      </dl>
      <div class="atlas__card-foot">
        ${renderSourceRef(f.source_ref)}
        <button type="button" class="atlas__link">${t("screen5.map.open_country")} →</button>
      </div>`;
    card.querySelector(".atlas__close")!.addEventListener("click", () => (card.hidden = true));
    card
      .querySelector(".atlas__link")!
      .addEventListener("click", () => navigate({ screen: "country", iso3: f.iso3 }));
  };

  const draw = (iso3: string) => {
    card.hidden = true;
    const points = bundle.rows.filter((f) => (f.mapped || f.approximate) && (!iso3 || f.iso3 === iso3));
    const selected = iso3 ? geo?.countries.features.find((f) => f.properties.iso3 === iso3) : undefined;
    let svg: SVGElement | HTMLElement;
    try {
      svg = plotMap(points, geo, iso3, selected);
    } catch (err) {
      // a damaged boundary file must never take the screen down: points only
      console.error(err);
      svg = plotMap(points, null, iso3, undefined);
    }
    canvas.replaceChildren(svg);
    // a click on a point opens its card: each mark's elements follow its data order
    for (const [cls, data] of [
      ["fm-exact", points.filter((p) => p.mapped)],
      ["fm-approx", points.filter((p) => p.approximate)],
    ] as const) {
      canvas.querySelectorAll(`g.${cls} > *`).forEach((el, i) => {
        const f = data[i];
        if (!f) return;
        el.setAttribute("tabindex", "0");
        el.setAttribute("role", "button");
        el.setAttribute("aria-label", f.name ?? f.facility_id);
        el.addEventListener("click", () => showCard(f));
        el.addEventListener("keydown", (e) => {
          if ((e as KeyboardEvent).key === "Enter") showCard(f);
        });
      });
    }
    title.textContent = iso3 ? (nameOf.get(iso3) ?? iso3) : t("screen5.map.all");
    reset.hidden = !iso3;
    stats.hidden = Boolean(iso3);
    for (const b of buttons) b.classList.toggle("is-active", b.dataset.iso3 === iso3);
    canvas.classList.remove("is-entering");
    void canvas.offsetWidth; // restart the entrance animation
    canvas.classList.add("is-entering");
  };
  for (const b of buttons) b.addEventListener("click", () => draw(b.dataset.iso3 ?? ""));
  reset.addEventListener("click", () => draw(""));
  draw("");
  return { select: draw };
}

function row(label: string, value: string | null | undefined): string {
  return value ? `<dt>${label}</dt><dd>${value}</dd>` : "";
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
  const exact = points.filter((p) => p.mapped);
  const approx = points.filter((p) => p.approximate);
  const active = exact.filter((p) => p.register_status === "active");
  // PEN-Plus country names in the region view; facility names in a country view
  const labelled = zoomed
    ? []
    : countries.filter((f) => f.properties.cohort !== null && f.properties.region === "AFRO");

  return Plot.plot({
    width: 1000,
    height: zoomed ? 760 : 860,
    margin: 0,
    projection: {
      type: "mercator",
      domain: (selected ?? REGION_FRAME) as never,
      inset: zoomed ? 46 : 8,
    },
    style: { fontFamily: "var(--font-family)", fontSize: "12px", background: "transparent" },
    symbol: { domain: STATUSES, range: STATUSES.map((s) => SYMBOL[s]) },
    marks: [
      Plot.graticule({ stroke: "rgba(255,255,255,0.06)" }),
      Plot.geo(countries, {
        fill: fillOf,
        stroke: BORDER,
        strokeWidth: zoomed ? 1.2 : 0.7,
        className: "fm-land",
      }),
      geo ? Plot.geo(geo.disputed_areas.features, { fill: "rgba(255,255,255,0.12)", stroke: "none" }) : null,
      geo
        ? Plot.geo(geo.disputed_borders.features, {
            stroke: "rgba(255,255,255,0.55)",
            strokeWidth: 1,
            strokeDasharray: "3,3",
          })
        : null,
      Plot.text(labelled, {
        x: (f: CountryFeature) => f.properties.lon,
        y: (f: CountryFeature) => f.properties.lat,
        text: (f: CountryFeature) => displayName(f.properties.name).toUpperCase(),
        fontSize: 8.5,
        fontWeight: 700,
        fill: "rgba(255,255,255,0.5)",
        lineWidth: 9,
        className: "fm-country-label",
      }),
      // soft halo under every active facility at its own coordinates
      Plot.dot(active, {
        x: "longitude",
        y: "latitude",
        r: zoomed ? 20 : 13,
        fill: "#9db3dd",
        fillOpacity: 0.22,
        className: "fm-halo",
      }),
      Plot.dot(approx, {
        x: "longitude",
        y: "latitude",
        symbol: "register_status",
        r: zoomed ? 8 : 5.5,
        fill: "transparent",
        stroke: POINT,
        strokeWidth: 1.8,
        strokeDasharray: "2.5,2",
        className: "fm-approx",
      }),
      Plot.dot(exact, {
        x: "longitude",
        y: "latitude",
        symbol: "register_status",
        r: zoomed ? 8.5 : 6,
        fill: POINT,
        stroke: "#0a1c45",
        strokeWidth: 1.5,
        className: "fm-exact",
      }),
      // facility names, alternating right and left so neighbours do not collide
      zoomed
        ? Plot.text(
            points.filter((_, i) => i % 2 === 1),
            {
              x: "longitude",
              y: "latitude",
              text: (f: FacilityRow) => f.name ?? f.facility_id,
              dx: -15,
              textAnchor: "end",
              fontSize: 12.5,
              fontWeight: 600,
              fill: "#ffffff",
              stroke: "#0a1c45",
              strokeWidth: 4,
              strokeOpacity: 0.85,
              paintOrder: "stroke",
              lineWidth: 18,
            },
          )
        : null,
      zoomed
        ? Plot.text(
            points.filter((_, i) => i % 2 === 0),
            {
              x: "longitude",
              y: "latitude",
              text: (f: FacilityRow) => f.name ?? f.facility_id,
              dx: 15,
              textAnchor: "start",
              fontSize: 12.5,
              fontWeight: 600,
              fill: "#ffffff",
              stroke: "#0a1c45",
              strokeWidth: 4,
              strokeOpacity: 0.85,
              paintOrder: "stroke",
              lineWidth: 18,
            },
          )
        : null,
    ],
  });
}
