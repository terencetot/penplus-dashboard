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

export { isLowCompleteness };
