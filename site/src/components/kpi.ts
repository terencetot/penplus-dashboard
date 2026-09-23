import { icon, type IconName } from "@/components/icons";

/**
 * The summary-before-detail row that opens screens 2-5, mirroring the hero
 * band's signal cards without their dark, "screen 1 only" treatment.
 *
 * Icon sits in its own tinted circular badge rather than floating bare above
 * the figure -- the badge is what actually reads as "designed" at a glance
 * (direct feedback: the plain top-left icon read as an afterthought), and it
 * doubles as the card's one status signal: muted grey when the figure itself
 * is null, the design system's primary tint otherwise. Colour still never
 * carries meaning alone -- the value text says "NR" regardless of the badge.
 */
export function renderKpiCard(iconName: IconName, value: string, label: string, isNull = false): string {
  return `<div class="kpi-card${isNull ? " is-null" : ""}">
    <div class="kpi-card__icon">${icon(iconName)}</div>
    <div class="kpi-card__body">
      <div class="kpi-card__value${isNull ? " is-null" : ""} num">${value}</div>
      <div class="kpi-card__label">${label}</div>
    </div>
  </div>`;
}

export function renderKpiRow(cards: string[]): string {
  return `<div class="kpi-row">${cards.join("")}</div>`;
}

/** A panel <h3> title with a small leading icon, for panels that open with a KPI row. */
export function panelTitleWithIcon(iconName: IconName, title: string): string {
  return `<div class="panel__title-row"><span class="panel__icon">${icon(iconName)}</span><h3 class="panel__title">${title}</h3></div>`;
}
