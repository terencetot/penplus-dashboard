import { getOverview } from "@/lib/bundle";
import { fmtCount, fmtDate } from "@/lib/format";
import { t } from "@/lib/i18n";
import { navigate } from "@/router";
import { renderSignalCard } from "@/components/figure-card";
import { renderMilestoneStrip } from "@/components/milestone-strip";
import type { CountryRef } from "@/lib/types";

/**
 * Screen 1: "Where is PEN-Plus and how big is it?" Order matters here --
 * the specification lists headline figures, then the situating grid, then
 * the milestone strip, and design language rule 5 (methodology) forbids the
 * grid from being the first element of the screen, so it never is.
 */
export async function renderOverview(container: HTMLElement): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const bundle = await getOverview();

  const heroAsOf = bundle.latest.find((v) => v.indicator_code === "2.5")?.as_of ?? null;

  container.innerHTML = `
    <div class="hero-band">
      <div class="hero-band__orb hero-band__orb--1"></div>
      <div class="hero-band__orb hero-band__orb--2"></div>
      <div class="hero-band__head">
        <h2 class="hero-band__title">${t("screen1.title")}</h2>
        <p class="hero-band__subtitle">${t("screen1.question")}</p>
      </div>
      <div class="hero-band__grid">
        ${renderSignalCard("facility", t("screen1.hero.facilities"), bundle.headline.facilities, heroAsOf)}
        ${renderSignalCard("patients", t("screen1.hero.ever_enrolled"), bundle.headline.ever_enrolled, heroAsOf)}
        ${renderSignalCard("pulse", t("screen1.hero.active"), bundle.headline.active, heroAsOf)}
        ${renderSignalCard("training", t("screen1.hero.trained"), bundle.headline.trained, heroAsOf)}
      </div>
    </div>

    <p class="exec-message">${t("screen1.summary", {
      countriesReporting: bundle.countries.filter((c) => c.returns > 0).length,
      countriesTotal: bundle.countries.length,
      facilities: fmtCount(bundle.headline.facilities.total),
      patients: fmtCount(bundle.headline.ever_enrolled.total),
    })}</p>

    <section class="panel">
      <div class="panel__header"><h3 class="panel__title">${t("screen1.map.title")}</h3></div>
      <div class="country-grid" id="country-grid"></div>
      <p class="chart-caption">${t("screen1.map.caption")}</p>
      <div class="chart-legend">
        <span class="chart-legend__item"><span class="chart-legend__swatch" style="background:var(--color-primary);opacity:.85"></span>${t("common.phase1")}</span>
        <span class="chart-legend__item"><span class="chart-legend__swatch" style="background:var(--color-primary);opacity:.4"></span>${t("common.phase2")}</span>
        <span class="chart-legend__item"><span class="chart-legend__swatch" style="background:var(--color-bg-muted)"></span>${t("status.not_reported")}</span>
      </div>
    </section>

    <section class="panel">
      <div class="panel__header"><h3 class="panel__title">${t("screen1.milestone.title")}</h3></div>
      ${renderMilestoneStrip(bundle.milestone_strip)}
      <p class="chart-caption">${t("screen1.milestone.caption")}</p>
    </section>
  `;

  const grid = container.querySelector<HTMLElement>("#country-grid")!;
  grid.className = "country-grid";
  for (const c of [...bundle.countries].sort((a: CountryRef, b: CountryRef) =>
    a.name.localeCompare(b.name),
  )) {
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = `country-tile ${c.returns > 0 ? (c.cohort === "phase_1" ? "is-phase1" : "is-phase2") : "is-none"}`;
    tile.textContent = c.iso3;
    tile.title = `${c.name} — ${c.returns > 0 ? `${t("common.as_of")} ${fmtDate(c.last_period)}` : t("status.not_reported")}`;
    tile.addEventListener("click", () => navigate({ screen: "country", iso3: c.iso3 }));
    grid.appendChild(tile);
  }
}
