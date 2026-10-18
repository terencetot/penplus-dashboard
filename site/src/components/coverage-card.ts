import { fmtCount } from "@/lib/format";
import { t } from "@/lib/i18n";

export interface CoverageFigure {
  total: number | null;
  countries_reporting: number;
  countries_total: number;
  coverage_pct: number | null;
  /** an open regional High query holding the total itself (e.g. Q-REG-01) */
  total_held_by?: string | null;
  /** countries whose own figure is held: published, never in the total */
  countries_held?: number;
}

/**
 * The richer KPI card used wherever country coverage is the point, not just
 * the value: the overview's headline figures and indicator detail's regional
 * card. Everything it shows -- total, coverage share, held counts -- is
 * computed in export.py (CLAUDE.md rule 1); this only renders it.
 *
 * Three states, each saying what it is in words (rule 9):
 *   - a total, with "Partial · x%" below 80 per cent coverage (rule 6);
 *   - "Held": a regional query holds the total; the countries behind it are
 *     still counted and published on the indicator screen;
 *   - "Not reported": no country has a figure.
 */
export function renderCoverageCard(
  label: string,
  figure: CoverageFigure,
  asOf?: string | null,
  /** Pre-formatted display value -- a rate's regional value is a 0-1
   * fraction, so the caller formats it (e.g. "19%"). */
  displayValue?: string,
  /** e.g. "ever enrolled", "active in care", "since the programme began" */
  valueType?: string,
): string {
  const coverage = `<b class="num">${t("common.n_of_total", { n: figure.countries_reporting, total: figure.countries_total })}</b> ${t("screen2.kpi.reporting").toLowerCase()}`;
  const heldNote =
    figure.countries_held && figure.countries_held > 0
      ? `<div class="coverage-card__held">${t("common.countries_held", { n: figure.countries_held })}</div>`
      : "";
  const pips = renderPips(figure.countries_reporting, figure.countries_total);
  const vt = valueType ? `<div class="value-type">${valueType}</div>` : "";

  if (figure.total_held_by) {
    return `<div class="coverage-card is-held">
      <div class="coverage-card__label">${label}</div>
      <div class="coverage-card__row">
        <div class="coverage-card__value">${t("prov.held")}</div>
        <span class="prov prov--held">${figure.total_held_by}</span>
      </div>
      <div class="coverage-card__note">${t("common.regional_total_held")}</div>
      <div class="coverage-card__cov">${coverage}</div>
      ${heldNote}
      ${pips}
    </div>`;
  }
  if (figure.total === null) {
    return `<div class="coverage-card is-nr">
      <div class="coverage-card__label">${label}</div>
      <div class="coverage-card__value">${t("status.not_reported")}</div>
      <div class="coverage-card__cov">${coverage}</div>
      ${heldNote}
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
    ${vt}
    <div class="coverage-card__cov">${coverage}${asOf ? ` &middot; ${t("common.as_of")} ${asOf}` : ""}</div>
    ${heldNote}
    ${pips}
  </div>`;
}

function renderPips(reporting: number, total: number): string {
  const pips = Array.from({ length: total }, (_, i) => `<i class="${i < reporting ? "f" : ""}"></i>`).join(
    "",
  );
  return `<div class="coverage-card__pips">${pips}</div>`;
}
