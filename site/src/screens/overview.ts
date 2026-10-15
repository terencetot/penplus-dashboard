import { getOverview } from "@/lib/bundle";
import { fmtCount } from "@/lib/format";
import { t } from "@/lib/i18n";
import { navigate } from "@/router";
import { renderCoverageCard } from "@/components/coverage-card";
import { renderMilestoneStrip } from "@/components/milestone-strip";
import { renderIsometricMap } from "@/components/country-tiles";
import type { CountryRef } from "@/lib/types";

/**
 * Screen 1: "Where is PEN-Plus and how big is it?" A dark hero states the
 * question and situates the region (the isometric country-tile map, cohort
 * only, never a value); the KPI band overlaps its lower edge with the four
 * headline figures and their coverage; milestone progress follows; the two
 * cohort lists close the screen as the least analytical content on the
 * page, same ordering rationale as before.
 */
export async function renderOverview(container: HTMLElement): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const bundle = await getOverview();

  const heroAsOf = bundle.latest.find((v) => v.indicator_code === "2.5")?.as_of ?? null;
  const allHistorical = bundle.latest.length > 0 && bundle.latest.every((v) => v.basis === "historical");
  const phase1 = bundle.countries.filter((c) => c.cohort === "phase_1");
  const phase2 = bundle.countries.filter((c) => c.cohort === "phase_2");
  const hasMilestones = bundle.milestone_strip.some((e) => e.milestone !== null);

  container.innerHTML = `
    <div class="hero">
      <div class="hero__grid">
        <div>
          ${allHistorical ? `<span class="chip">${t("screen1.hero.historical_chip")}</span>` : ""}
          <h1>${t("screen1.title")}</h1>
          <p class="q">${t("screen1.question")}</p>
          <p class="sum">${t("screen1.summary", {
            countriesReporting: bundle.countries.filter((c) => c.returns > 0).length,
            countriesTotal: bundle.countries.length,
            facilities: fmtCount(bundle.headline.facilities.total),
            patients: fmtCount(bundle.headline.ever_enrolled.total),
          })}</p>
          <div class="leg">
            <span><i class="a"></i>${t("screen1.hero.phase1_legend", { n: phase1.length })}</span>
            <span><i class="b"></i>${t("screen1.hero.phase2_legend", { n: phase2.length })}</span>
          </div>
        </div>
        ${renderIsometricMap(bundle.countries)}
      </div>
    </div>

    <div class="kpi-band">
      <div class="coverage-row">
        ${renderCoverageCard(t("screen1.hero.facilities"), bundle.headline.facilities, heroAsOf)}
        ${renderCoverageCard(t("screen1.hero.ever_enrolled"), bundle.headline.ever_enrolled, heroAsOf)}
        ${renderCoverageCard(t("screen1.hero.active"), bundle.headline.active, heroAsOf)}
        ${renderCoverageCard(t("screen1.hero.trained"), bundle.headline.trained, heroAsOf)}
      </div>
    </div>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3 class="panel__title">${t("screen1.milestone.title")}</h3>
        </div>
        ${!hasMilestones ? `<span class="chip chip--warm">${t("screen1.milestone.not_published")}</span>` : ""}
      </div>
      ${renderMilestoneStrip(bundle.milestone_strip)}
      <p class="chart-caption">${t("screen1.milestone.caption")}</p>
    </section>

    <div class="cohort-grid" id="cohort-grid"></div>
  `;

  const grid = container.querySelector<HTMLElement>("#cohort-grid")!;
  grid.append(
    buildCohortPanel(t("common.phase1"), t("screen1.cohort.returns_on_file", { n: phase1.length }), phase1),
    buildCohortPanel(t("common.phase2"), t("screen1.cohort.countries_count", { n: phase2.length }), phase2),
  );
}

function buildCohortPanel(title: string, subtitle: string, countries: CountryRef[]): HTMLElement {
  const panel = document.createElement("div");
  panel.className = "panel cohort-panel";
  panel.innerHTML = `<h3>${title} <small>${subtitle}</small></h3><div class="cohort-list"></div>
    <p class="chart-caption">${t("screen1.cohort.footnote")}</p>`;
  const list = panel.querySelector(".cohort-list")!;
  for (const c of [...countries].sort((a, b) => a.name.localeCompare(b.name))) {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "cohort-row";
    const pips =
      c.returns > 0
        ? `<span class="cohort-row__pips" title="${c.returns} ${t("screen3.kpi.returns").toLowerCase()}">${Array.from(
            { length: 5 },
            (_, i) => `<i class="${i < c.returns ? "f" : ""}"></i>`,
          ).join("")}</span><small class="num">${c.last_period ?? ""}</small>`
        : `<small class="aw">${t("screen1.cohort.no_return")}</small>`;
    row.innerHTML = `<b>${c.name}</b>${pips}`;
    row.addEventListener("click", () => navigate({ screen: "country", iso3: c.iso3 }));
    list.appendChild(row);
  }
  return panel;
}
