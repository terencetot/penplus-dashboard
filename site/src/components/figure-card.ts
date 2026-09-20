import { fmtCount } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { HeadlineFigure } from "@/lib/types";

/**
 * Screen 1's four headline figures. Specification: "A headline figure
 * without its completeness is not displayed" -- here that means the
 * reporting share is always rendered alongside the number, never hidden
 * behind a hover, and a null total renders as an explicit NR, not a 0.
 */
export function renderFigureCard(label: string, figure: HeadlineFigure, asOf?: string | null): string {
  const isNull = figure.total === null;
  return `<div class="figure-card${isNull ? " is-muted" : ""}">
    <div class="figure-card__label">${label}</div>
    <div class="figure-card__value num${isNull ? " is-null" : ""}">${fmtCount(figure.total)}</div>
    <div class="figure-card__meta">${t("screen1.hero.reporting", { n: figure.countries_reporting, N: figure.countries_total })}${asOf ? ` &middot; ${t("common.as_of")} ${asOf}` : ""}</div>
  </div>`;
}
