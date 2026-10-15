import type { CountryRef } from "@/lib/types";

/**
 * The hero's isometric country-tile map. Layout is fixed decorative
 * artwork -- a hand-arranged grid position per country plus empty filler
 * cells, in --s (50px) units -- not generated from data, so it can never
 * accidentally encode a value. The one thing that IS read from data is
 * which of the two tile styles a country gets: p1 (raised, solid) for the
 * Phase 1 cohort, p2 (low, glass) for Phase 2. Every tile is the same
 * height within its own style -- cohort is the only thing a reader can
 * take from this map, never a count, a rate or a ranking (design brief:
 * "uniform height encodes cohort only, never a value").
 */
const TILE_LAYOUT: { iso3: string; left: number; top: number }[] = [
  { iso3: "GHA", left: 171, top: 114 },
  { iso3: "SWZ", left: 570, top: 399 },
  { iso3: "SEN", left: 114, top: 57 },
  { iso3: "BWA", left: 513, top: 342 },
  { iso3: "UGA", left: 570, top: 171 },
  { iso3: "NGA", left: 342, top: 114 },
  { iso3: "TZA", left: 627, top: 228 },
  { iso3: "ETH", left: 570, top: 114 },
  { iso3: "BEN", left: 285, top: 114 },
  { iso3: "ZMB", left: 513, top: 285 },
  { iso3: "GAB", left: 399, top: 228 },
  { iso3: "COD", left: 513, top: 171 },
  { iso3: "MOZ", left: 627, top: 285 },
  { iso3: "KEN", left: 627, top: 171 },
  { iso3: "ZWE", left: 570, top: 342 },
  { iso3: "MWI", left: 570, top: 285 },
  { iso3: "LSO", left: 513, top: 456 },
  { iso3: "LBR", left: 114, top: 171 },
  { iso3: "CMR", left: 399, top: 114 },
  { iso3: "SLE", left: 57, top: 171 },
  { iso3: "BFA", left: 228, top: 57 },
  { iso3: "TGO", left: 228, top: 114 },
  { iso3: "NER", left: 285, top: 57 },
  { iso3: "GMB", left: 57, top: 57 },
  { iso3: "CPV", left: 0, top: 0 },
  { iso3: "MLI", left: 171, top: 57 },
  { iso3: "COG", left: 456, top: 171 },
  { iso3: "RWA", left: 570, top: 228 },
  { iso3: "AGO", left: 456, top: 228 },
  { iso3: "BDI", left: 513, top: 228 },
  { iso3: "SSD", left: 513, top: 114 },
];

const OFF_CELLS: { left: number; top: number }[] = [
  { left: 456, top: 285 },
  { left: 741, top: 228 },
  { left: 741, top: 342 },
  { left: 171, top: 0 },
  { left: 114, top: 114 },
  { left: 684, top: 342 },
  { left: 228, top: 0 },
  { left: 513, top: 399 },
  { left: 456, top: 114 },
  { left: 570, top: 57 },
  { left: 684, top: 285 },
  { left: 342, top: 171 },
  { left: 342, top: 57 },
  { left: 57, top: 114 },
  { left: 399, top: 171 },
  { left: 0, top: 114 },
];

const PLANE_W = 798;
const PLANE_H = 513;
const TILE_S = 50;

/** Absolute, not relative: a relative url() handed to CSS through a custom
 * property resolves against the stylesheet that consumes it (dist/assets/),
 * not the page, and every mask silently 404s under `base: "./"`. */
function maskUrl(iso3: string): string {
  return new URL(`${import.meta.env.BASE_URL}assets/country-masks/${iso3}.png`, document.baseURI).href;
}

export function renderIsometricMap(countries: CountryRef[]): string {
  const byIso3 = new Map(countries.map((c) => [c.iso3, c]));
  const tiles = TILE_LAYOUT.map(({ iso3, left, top }) => {
    const c = byIso3.get(iso3);
    if (!c) return "";
    const cls = c.cohort === "phase_1" ? "p1" : "p2";
    return `<div class="t ${cls}" style="left:${left}px;top:${top}px" title="${c.name}">
      <span class="m" style="--m:url('${maskUrl(iso3)}')"></span><em>${iso3}</em>
    </div>`;
  }).join("");
  const off = OFF_CELLS.map(
    ({ left, top }) => `<div class="t off" style="left:${left}px;top:${top}px"></div>`,
  ).join("");
  return `<div class="iso">
    <div class="plane" style="width:${PLANE_W}px;height:${PLANE_H}px;--s:${TILE_S}px">
      ${tiles}${off}
    </div>
  </div>`;
}

/** The single enlarged tile used as a country's own badge on its profile
 * (screen 3): the same mark, the same two styles, just one tile and no grid. */
export function renderCountryTileBadge(
  iso3: string,
  cohort: CountryRef["cohort"],
  cohortLabel: string,
): string {
  const cls = cohort === "phase_1" ? "p1" : "p2";
  return `<div class="country-badge">
    <div class="iso country-badge__iso">
      <div class="plane" style="--s:150px;width:150px;height:150px">
        <div class="t ${cls}" style="left:0;top:0">
          <span class="m" style="--m:url('${maskUrl(iso3)}')"></span>
        </div>
      </div>
    </div>
    <span class="country-badge__label">${cohortLabel}</span>
  </div>`;
}
