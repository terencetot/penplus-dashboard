/**
 * Every formatter here follows CLAUDE.md rule 2: "Null is not zero." A `null`
 * or `undefined` numeric value must render as an explicit gap (`NR`), never
 * as 0, never as an empty string that could be misread as 0. Nothing in this
 * module performs arithmetic; it only formats numbers the pipeline already
 * computed (rule 1, "No arithmetic in the front end").
 */

const INT = new Intl.NumberFormat("en", { maximumFractionDigits: 0 });
const PCT = new Intl.NumberFormat("en", { style: "percent", maximumFractionDigits: 0 });
const PCT1 = new Intl.NumberFormat("en", { style: "percent", maximumFractionDigits: 1 });

export const NR = "NR";

/** An integer count, or the NR marker if the value was not reported. */
export function fmtCount(value: number | null | undefined): string {
  return value === null || value === undefined ? NR : INT.format(value);
}

/** A 0-1 fraction as a percentage, or NR. `value` must already be numerator/denominator. */
export function fmtRate(value: number | null | undefined, precise = false): string {
  if (value === null || value === undefined) return NR;
  return (precise ? PCT1 : PCT).format(value);
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
  return `${fmtRate(value)} (n=${INT.format(numerator)} of N=${INT.format(denominator)})`;
}

export function fmtNandN(numerator: number | null, denominator: number | null): string {
  if (numerator === null || denominator === null) return NR;
  return `n=${INT.format(numerator)} of N=${INT.format(denominator)}`;
}

/** ISO date -> a short, locale-neutral display date. Never guesses a date. */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return NR;
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00Z" : ""));
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("en", {
    year: "numeric",
    month: "short",
    day: "2-digit",
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
    : PCT.format(completeness);
}

/** A rate built on fewer than twenty patients needs its confidence flagged (spec 3.1). */
export const SMALL_N_THRESHOLD = 20;

export function isSmallN(denominator: number | null | undefined): boolean {
  return denominator !== null && denominator !== undefined && denominator < SMALL_N_THRESHOLD;
}
