import { t } from "@/lib/i18n";
import { icon } from "@/components/icons";

/**
 * The element every chart function returns when it has nothing to draw --
 * e.g. every value in the series is NR. Observable Plot renders a
 * degenerate, oversized frame when a scale's domain collapses to nothing
 * (an all-NaN y channel), so callers must not hand it an empty domain and
 * hope; they check first and show this instead. Matches CLAUDE.md's own
 * rule: "Where a screen looks empty, that is the real state of the
 * evidence and the screen must say so rather than being filled with a
 * placeholder."
 */
export function emptyChart(height = 120, message?: string): HTMLElement {
  const el = document.createElement("div");
  el.className = "chart-empty";
  el.style.minHeight = `${height}px`;
  el.innerHTML = `<span class="chart-empty__icon">${icon("map")}</span><span class="chart-empty__text"></span>`;
  el.querySelector(".chart-empty__text")!.textContent = message ?? t("empty.no_data");
  return el;
}
