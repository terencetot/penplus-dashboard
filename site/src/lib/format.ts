/**
 * Every formatter here follows CLAUDE.md rule 2: "Null is not zero." A `null`
 * or `undefined` numeric value must render as an explicit gap (`NR`), never
 * as 0, never as an empty string that could be misread as 0. Nothing in this
 * module performs arithmetic; it only formats numbers the pipeline already
 * computed (rule 1, "No arithmetic in the front end").
 */

import { getLang } from "./i18n";

/** Number formats follow the interface language: 6,324 / 6 324 / 6 324. */
const LOCALE: Record<string, string> = { en: "en-GB", fr: "fr-FR", pt: "pt-PT" };
const cache = new Map<string, Intl.NumberFormat>();
function nf(kind: "int" | "pct" | "pct1"): Intl.NumberFormat {
  const locale = LOCALE[getLang()] ?? "en-GB";
  const key = `${locale}:${kind}`;
  if (!cache.has(key)) {
    cache.set(
      key,
      new Intl.NumberFormat(
        locale,
        kind === "int"
          ? // "always": Portuguese otherwise writes 4590 next to 17 500
            ({ maximumFractionDigits: 0, useGrouping: "always" } as unknown as Intl.NumberFormatOptions)
          : { style: "percent", maximumFractionDigits: kind === "pct" ? 0 : 1 },
      ),
    );
  }
  return cache.get(key)!;
}

export const NR = "NR";

/** French writes thousands with a narrow no-break space (U+202F); at display
 * size and tight tracking it vanishes ("170000"). A full no-break space keeps
 * the groups readable and never breaks a number across lines. */
const NARROW_NBSP = /\u202f/g;

/** An integer count, or the NR marker if the value was not reported. */
export function fmtCount(value: number | null | undefined): string {
  return value === null || value === undefined ? NR : nf("int").format(value).replace(NARROW_NBSP, "\u00a0");
}

/**
 * The same count as HTML for tabular columns: the digits stay tabular so a
 * column aligns, but the thousands separator is set in proportional figures
 * (`.nsep`) -- the display font's tabular comma is a full figure wide and
 * reads as "1 , 121".
 */
export function fmtCountHtml(value: number | null | undefined): string {
  if (value === null || value === undefined) return NR;
  return nf("int")
    .formatToParts(value)
    .map((p) =>
      p.type === "group" ? `<span class="nsep">${p.value.replace(NARROW_NBSP, "\u00a0")}</span>` : p.value,
    )
    .join("");
}

/** A 0-1 fraction as a percentage, or NR. `value` must already be numerator/denominator. */
/** A programme figure, as HTML: "+170,000" when the figure is a floor, the
 * "+" set lighter and smaller than the digits (`.num-plus`). */
export function fmtProgramme(f: { value: number; at_least: boolean } | null | undefined): string {
  if (!f) return "—";
  return `${f.at_least ? `<span class="num-plus">+</span>` : ""}${fmtCount(f.value)}`;
}

export function fmtRate(value: number | null | undefined, precise = false): string {
  if (value === null || value === undefined) return NR;
  return nf(precise ? "pct1" : "pct").format(value);
}

/**
 * Display rule 1 (specification, section 3): never a rate without n and N.
 * Returns the full "62% (n=93 of N=150)" style string, or NR when either
 * part is missing -- the rate itself must not render if its parts cannot.
 */
export function fmtRateWithNandN(
  numerator: number | null,
  denominator: number | null,
  value: number | null,
): string {
  if (numerator === null || denominator === null || value === null) return NR;
  return `${fmtRate(value)} (n=${nf("int").format(numerator)} of N=${nf("int").format(denominator)})`;
}

export function fmtNandN(numerator: number | null, denominator: number | null): string {
  if (numerator === null || denominator === null) return NR;
  return `n=${nf("int").format(numerator)} of N=${nf("int").format(denominator)}`;
}

/** ISO date -> a short, locale-neutral display date. Never guesses a date. */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return NR;
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00Z" : ""));
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(LOCALE[getLang()] ?? "en-GB", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  }).format(d);
}

/** Display rule 4: completeness travels with the figure; below 80% the figure is muted. */
export const COMPLETENESS_THRESHOLD = 0.8;

export function isLowCompleteness(completeness: number | null | undefined): boolean {
  return completeness !== null && completeness !== undefined && completeness < COMPLETENESS_THRESHOLD;
}

export function fmtCompletenessShare(completeness: number | null | undefined): string {
  return completeness === null || completeness === undefined
    ? "completeness not reported"
    : nf("pct").format(completeness);
}

/** A rate built on fewer than twenty patients needs its confidence flagged (spec 3.1). */
export const SMALL_N_THRESHOLD = 20;

export function isSmallN(denominator: number | null | undefined): boolean {
  return denominator !== null && denominator !== undefined && denominator < SMALL_N_THRESHOLD;
}
