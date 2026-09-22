import { icon, type IconName } from "@/components/icons";

/**
 * The summary-before-detail row that opens screens 2-5, mirroring the hero
 * band's signal cards without their dark, "screen 1 only" treatment.
 */
export function renderKpiCard(iconName: IconName, value: string, label: string, isNull = false): string {
  return `<div class="kpi-card">
    <div class="kpi-card__icon">${icon(iconName)}</div>
    <div class="kpi-card__value${isNull ? " is-null" : ""} num">${value}</div>
    <div class="kpi-card__label">${label}</div>
  </div>`;
}

export function renderKpiRow(cards: string[]): string {
  return `<div class="kpi-row">${cards.join("")}</div>`;
}

/** A panel <h3> title with a small leading icon, for panels that open with a KPI row. */
export function panelTitleWithIcon(iconName: IconName, title: string): string {
  return `<div class="panel__title-row"><span class="panel__icon">${icon(iconName)}</span><h3 class="panel__title">${title}</h3></div>`;
}
