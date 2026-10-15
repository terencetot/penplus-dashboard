import { fmtCount } from "@/lib/format";
import { t } from "@/lib/i18n";

export interface CoverageFigure {
  total: number | null;
  countries_reporting: number;
  countries_total: number;
  coverage_pct: number | null;
}

/**
 * The richer KPI card used wherever country-coverage is the point, not
 * just the value: the overview hero's four headline figures, and
 * indicator detail's regional-value card. `coverage_pct` is computed once
 * in export.py (CLAUDE.md rule 1) -- this renders it, it never divides
 * countries_reporting by countries_total itself.
 */
export function renderCoverageCard(
  label: string,
  figure: CoverageFigure,
  asOf?: string | null,
  /** Pre-formatted display value -- a rate indicator's regional_value is a
   * 0-1 fraction, not a count, so the caller formats it (e.g. "19%") rather
   * than this component guessing a unit it is never told. */
  displayValue?: string,
): string {
  const coverage = `<b class="num">${t("common.n_of_total", { n: figure.countries_reporting, total: figure.countries_total })}</b> ${t("screen2.kpi.reporting").toLowerCase()}`;
  const pips = renderPips(figure.countries_reporting, figure.countries_total);

  if (figure.total === null) {
    return `<div class="coverage-card is-nr">
      <div class="coverage-card__label">${label}</div>
      <div class="coverage-card__value">${t("status.not_reported")}</div>
      <div class="coverage-card__cov">${coverage}</div>
      ${pips}
    </div>`;
  }
  // CLAUDE.md rule 6: below 80 per cent the value renders muted, with the
  // share visible without interaction
  const isPartial = figure.coverage_pct !== null && figure.coverage_pct < 80;
  return `<div class="coverage-card${isPartial ? " partial" : ""}">
    <div class="coverage-card__label">${label}</div>
    <div class="coverage-card__row">
      <div class="coverage-card__value num">${displayValue ?? fmtCount(figure.total)}</div>
      ${isPartial ? `<span class="chip chip--warm">${t("common.partial")} &middot; ${figure.coverage_pct}%</span>` : ""}
    </div>
    <div class="coverage-card__cov">${coverage}${asOf ? ` &middot; ${t("common.as_of")} ${asOf}` : ""}</div>
    ${pips}
  </div>`;
}

function renderPips(reporting: number, total: number): string {
  const pips = Array.from({ length: total }, (_, i) => `<i class="${i < reporting ? "f" : ""}"></i>`).join(
    "",
  );
  return `<div class="coverage-card__pips">${pips}</div>`;
}
