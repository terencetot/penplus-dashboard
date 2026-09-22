import { fmtCompletenessShare, isLowCompleteness } from "@/lib/format";

/**
 * Display rule 4: "Completeness travels with the figure. Below 80 per cent
 * the figure is displayed in a muted state with the share visible without
 * interaction" -- so this renders inline, not behind a hover/tooltip.
 */
export function renderCompleteness(completeness: number | null): string {
  const low = isLowCompleteness(completeness);
  const pct = completeness === null ? 0 : Math.max(0, Math.min(1, completeness));
  return `<span class="completeness${low ? " is-low" : ""}">
    <span class="completeness__bar"><span style="width:${(pct * 100).toFixed(0)}%"></span></span>
    ${fmtCompletenessShare(completeness)}
  </span>`;
}

/**
 * The lightweight sibling of `renderCompleteness` for a value cell that
 * already has its own formatting (a table's "value" column, a trend point):
 * mute the text and show the share next to it, rather than replacing it with
 * a progress bar. Same rule (4), applied wherever a country-level figure is
 * printed, not only in the dedicated completeness column.
 */
export function renderValueWithCompleteness(text: string, completeness: number | null): string {
  if (!isLowCompleteness(completeness)) return text;
  return `<span class="value-completeness is-low">${text}
    <small>(${fmtCompletenessShare(completeness)})</small>
  </span>`;
}

export { isLowCompleteness };
