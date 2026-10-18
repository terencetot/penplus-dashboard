import { fmtCount } from "@/lib/format";
import { t } from "@/lib/i18n";

/**
 * The figure tile used on every screen: label, one large value, a short
 * explanation and, when the figure is a regional total, its country coverage
 * written and drawn (one pip per country). Values arrive pre-computed from
 * export.py; below 80 per cent coverage the value is muted (CLAUDE.md rule 6),
 * never flagged in orange (orange is for alerts).
 */
export function statTile(label: string, value: string, sub = "", extraClass = ""): string {
  return `<div class="stat ${extraClass}"><span class="stat__label">${label}</span>
    <b class="stat__value num">${value}</b>${sub ? `<span class="stat__sub">${sub}</span>` : ""}</div>`;
}

export interface Coverage {
  countries_reporting: number;
  countries_total: number;
  coverage_pct: number | null;
}

export function coverageTile(label: string, value: string, sub: string, c: Coverage): string {
  const partial = c.coverage_pct !== null && c.coverage_pct < 80;
  const pips = Array.from(
    { length: c.countries_total },
    (_, i) => `<i class="${i < c.countries_reporting ? "f" : ""}"></i>`,
  ).join("");
  return `<div class="stat${partial ? " is-partial" : ""}"><span class="stat__label">${label}</span>
    <b class="stat__value num">${value}</b>
    ${sub ? `<span class="stat__sub">${sub}</span>` : ""}
    <span class="stat__cov">${t("screen1.kpi.coverage", { n: c.countries_reporting, total: c.countries_total })}</span>
    <span class="stat__pips" aria-hidden="true">${pips}</span></div>`;
}

export function countValue(v: number | null): string {
  return v === null ? "—" : fmtCount(v);
}
