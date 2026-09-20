import { fmtCount, fmtDate, NR } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { MilestoneStripEntry } from "@/lib/types";

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
      const gapText =
        e.gap === null
          ? t("common.no_milestone")
          : `${t("common.gap_to_milestone")}: ${fmtCount(Math.abs(e.gap))}`;
      return `<div class="milestone-row${hasMilestone ? "" : " milestone-row--no-target"}">
        <div class="milestone-row__label">${e.label_en}<small>${e.as_of ? `${t("common.as_of")} ${fmtDate(e.as_of)}` : ""}</small></div>
        <div class="milestone-row__track" role="img" aria-label="${e.label_en}: ${valueText}${hasMilestone ? `, ${t("common.gap_to_milestone").toLowerCase()} ${fmtCount(e.gap)}` : ""}">
          ${hasMilestone ? `<div class="milestone-row__fill" style="width:${pct}%"></div><div class="milestone-row__target" style="left:100%"></div>` : ""}
        </div>
        <div class="milestone-row__value num">${valueText}<span class="gap">${gapText}</span></div>
      </div>`;
    })
    .join("");
}
