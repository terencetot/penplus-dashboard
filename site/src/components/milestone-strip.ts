import { fmtCount, fmtDate, NR } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { MilestoneStripEntry } from "@/lib/types";

/**
 * A positive gap is a shortfall, a negative gap is over-achievement, and
 * `Math.abs` used to erase that sign (306 against a milestone of 120 read
 * "Gap to milestone: 186" instead of "Milestone exceeded by 186"). Exported
 * so every other place a `gap` field is printed applies the same three-way
 * reading, not just this strip.
 */
export function gapText(gap: number | null): string {
  if (gap === null) return t("common.no_milestone");
  if (gap === 0) return t("common.milestone_met");
  if (gap < 0) return `${t("common.milestone_exceeded_by")}: ${fmtCount(-gap)}`;
  return `${t("common.gap_to_milestone")}: ${fmtCount(gap)}`;
}

/**
 * Screen 1's milestone strip: "the last value, the milestone and the gap, as
 * a horizontal bar against a target marker. Not a gauge, not a dial, not a
 * traffic light" (specification, screen 1 in detail). No milestone value has
 * been published yet for any indicator (see docs/architecture.md), so every
 * row currently renders its value with an explicit "milestone not yet
 * published" state rather than a bar computed against nothing -- the moment
 * dim_indicator.milestone is set, the same markup starts drawing the bar.
 */
export function renderMilestoneStrip(entries: MilestoneStripEntry[]): string {
  return entries
    .map((e) => {
      const hasMilestone = e.milestone !== null && e.value !== null;
      const pct = hasMilestone ? Math.max(0, Math.min(100, (e.value! / e.milestone!) * 100)) : 0;
      const valueText = e.value === null ? NR : fmtCount(e.value);
      const gap = gapText(e.gap);
      return `<div class="milestone-row${hasMilestone ? "" : " milestone-row--no-target"}">
        <div class="milestone-row__label">${e.label_en}<small>${e.as_of ? `${t("common.as_of")} ${fmtDate(e.as_of)}` : ""}</small></div>
        <div class="milestone-row__track" role="img" aria-label="${e.label_en}: ${valueText}${hasMilestone ? `, ${gap.toLowerCase()}` : ""}">
          ${hasMilestone ? `<div class="milestone-row__fill" style="width:${pct}%"></div><div class="milestone-row__target" style="left:100%"></div>` : ""}
        </div>
        <div class="milestone-row__value num">${valueText}<span class="gap">${gap}</span></div>
      </div>`;
    })
    .join("");
}
