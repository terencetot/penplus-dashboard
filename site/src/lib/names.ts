import { getLang, t } from "./i18n";

/**
 * Display names in the interface language. The bundle carries English names
 * (from the pipeline); the site translates them here, at display time, so a
 * French or Portuguese reader never meets an English country or indicator
 * name in an otherwise translated screen. Unknown codes fall back to the
 * bundle's own English text.
 */
export function countryName(iso3: string, fallback: string): string {
  const key = `country.${iso3}`;
  const v = t(key);
  return v === key ? fallback : v;
}

export function indicatorLabel(code: string, fallback: string): string {
  const key = `ind.${code}.label`;
  const v = t(key);
  return v === key ? fallback : v;
}

export function indicatorDefinition(code: string, fallback: string | null): string | null {
  const key = `ind.${code}.definition`;
  const v = t(key);
  return v === key ? fallback : v;
}

/** Alphabetical comparison in the reader's language (rule 5: order, never rank). */
export function byName(a: string, b: string): number {
  return a.localeCompare(b, getLang());
}

export function phaseLabel(phaseNo: number, fallback: string): string {
  const key = `phase.${phaseNo}`;
  const v = t(key);
  return v === key ? fallback : v;
}

export function stepLabel(stepNo: number, fallback: string): string {
  const key = `step.${stepNo}`;
  const v = t(key);
  return v === key ? fallback : v;
}
