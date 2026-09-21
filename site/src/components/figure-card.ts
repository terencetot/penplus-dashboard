import { fmtCount } from "@/lib/format";
import { t } from "@/lib/i18n";
import { icon, type IconName } from "@/components/icons";
import type { HeadlineFigure } from "@/lib/types";

/**
 * Screen 1's four headline figures, rendered as the hero band's icon-led
 * "signal cards". Specification: "A headline figure without its
 * completeness is not displayed" -- the reporting share is always rendered
 * alongside the number, never hidden behind a hover, and a null total
 * renders as an explicit NR, not a 0.
 */
export function renderSignalCard(
  iconName: IconName,
  label: string,
  figure: HeadlineFigure,
  asOf?: string | null,
): string {
  const isNull = figure.total === null;
  return `<div class="signal-card">
    <div class="signal-card__icon">${icon(iconName)}</div>
    <div class="signal-card__value num${isNull ? " is-null" : ""}">${fmtCount(figure.total)}</div>
    <div class="signal-card__label">${label}</div>
    <div class="signal-card__meta">${t("screen1.hero.reporting", { n: figure.countries_reporting, N: figure.countries_total })}${asOf ? ` &middot; ${t("common.as_of")} ${asOf}` : ""}</div>
  </div>`;
}
