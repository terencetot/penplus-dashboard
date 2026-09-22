import type {
  CountryBundle,
  FacilitiesBundle,
  ImplementationBundle,
  IndicatorsBundle,
  Manifest,
  OverviewBundle,
  QualityBundle,
} from "./types";
import { isDemoMode } from "./demo";

/**
 * The bundle is the API (specification, section 5). Every fetch here is a
 * same-origin static file under /data (site/public/data at build time, so
 * Vite copies it verbatim), produced by the pipeline and never hand-edited.
 * No other network call exists anywhere in this app. Demo mode (see
 * lib/demo.ts) points this at /demo-data instead -- a wholly synthetic
 * bundle, never mixed with the real one.
 */
function dataRoot(): string {
  const dir = isDemoMode() ? "demo-data" : "data";
  return `${import.meta.env.BASE_URL}${dir}/`;
}

const cache = new Map<string, Promise<unknown>>();

async function getJSON<T>(path: string): Promise<T> {
  const cacheKey = `${isDemoMode() ? "demo:" : "real:"}${path}`;
  if (!cache.has(cacheKey)) {
    const url = dataRoot() + path;
    cache.set(
      cacheKey,
      fetch(url).then((res) => {
        if (!res.ok) {
          throw new Error(`bundle fetch failed: ${path} (${res.status})`);
        }
        return res.json();
      }),
    );
  }
  return cache.get(cacheKey) as Promise<T>;
}

export const getManifest = () => getJSON<Manifest>("manifest.json");
export const getOverview = () => getJSON<OverviewBundle>("overview.json");
export const getIndicators = () => getJSON<IndicatorsBundle>("indicators.json");
export const getQuality = () => getJSON<QualityBundle>("quality.json");
export const getFacilities = () => getJSON<FacilitiesBundle>("facilities.json");
export const getImplementation = () => getJSON<ImplementationBundle>("implementation.json");
export const getCountry = (iso3: string) => getJSON<CountryBundle>(`countries/${iso3}.json`);

/** The distinct period_ids in the current bundle, oldest first. */
export function periodsOf(manifest: Manifest): string[] {
  return manifest.periods
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean);
}

/** True once Phase Two periods (any period from 2026 on, per CLAUDE.md's cohort note) begin. */
export function isPhaseTwoPeriod(periodId: string): boolean {
  const year = Number.parseInt(periodId.slice(0, 4), 10);
  return Number.isFinite(year) && year >= 2026;
}
