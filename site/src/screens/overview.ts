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
 * question and situates the region (the isometric country-tile map: cohort
 * only, uniform height, never a value); the KPI band overlaps its lower edge
 * with the headline figures and their coverage; milestone progress follows;
 * the two cohort lists close the screen.
 *
 * Patients are split into the sentinel conditions (2.6) and all PEN-Plus
 * conditions (2.5), the new national tool's definitions. While query
 * Q-REG-01 is open the regional patient totals are held: the cards say so and
 * keep their country coverage; the country figures are on screen 2.
 */
export async function renderOverview(container: HTMLElement): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const bundle = await getOverview();
  const h = bundle.headline;

  const allHistorical = bundle.latest.length > 0 && bundle.latest.every((v) => v.basis === "historical");
  const round1 = bundle.countries.filter((c) => c.cohort === "phase_1");
  const round2 = bundle.countries.filter((c) => c.cohort === "phase_2");
  const hasMilestones = bundle.milestone_strip.some((e) => e.milestone !== null);

  container.innerHTML = `
    <div class="hero">
      <div class="hero__grid">
        <div>
          ${allHistorical ? `<span class="chip">${t("screen1.hero.historical_chip")}</span>` : ""}
          <h1>${t("screen1.title")}</h1>
          <p class="q">${t("screen1.question")}</p>
          <p class="sum">${t("screen1.summary", {
            countriesReporting: bundle.countries_with_data,
            countriesTotal: bundle.countries.length,
            facilities: fmtCount(h.facilities.total),
            facilityCountries: h.facilities.countries_reporting,
          })}</p>
          <div class="leg">
            <span><i class="a"></i>${t("screen1.hero.phase1_legend", { n: round1.length })}</span>
            <span><i class="b"></i>${t("screen1.hero.phase2_legend", { n: round2.length })}</span>
          </div>
        </div>
        ${renderIsometricMap(bundle.countries)}
      </div>
    </div>

    <div class="kpi-band">
      <div class="coverage-row coverage-row--5">
        ${renderCoverageCard(t("screen1.hero.facilities"), h.facilities, null, undefined, t("value_type.register"))}
        ${renderCoverageCard(t("screen1.hero.sentinel"), h.sentinel_ever, null, undefined, t("value_type.ever_sentinel"))}
        ${renderCoverageCard(t("screen1.hero.all_conditions"), h.all_ever, null, undefined, t("value_type.ever_all"))}
        ${renderCoverageCard(t("screen1.hero.active"), h.sentinel_active, null, undefined, t("value_type.active"))}
        ${renderCoverageCard(t("screen1.hero.trained"), h.trained, null, undefined, t("value_type.to_date"))}
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
    buildCohortPanel(
      t("common.phase1"),
      t("screen1.cohort.countries_count", { n: round1.length }),
      round1,
      "phase_1",
    ),
    buildCohortPanel(
      t("common.phase2"),
      t("screen1.cohort.countries_count", { n: round2.length }),
      round2,
      "phase_2",
    ),
  );
}

function buildCohortPanel(
  title: string,
  subtitle: string,
  countries: CountryRef[],
  cohort: "phase_1" | "phase_2",
): HTMLElement {
  const panel = document.createElement("div");
  panel.className = `panel cohort-panel cohort-panel--${cohort}`;
  panel.innerHTML = `<h3>${title} <small>${subtitle}</small></h3><div class="cohort-list"></div>
    <p class="chart-caption">${t("screen1.cohort.footnote")}</p>`;
  const list = panel.querySelector(".cohort-list")!;
  for (const c of [...countries].sort((a, b) => a.name.localeCompare(b.name))) {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "cohort-row";
    // The implementation phase is published from the official ICPPA 2026
    // map; a country with no return yet says exactly that -- never "not
    // started", never omitted (audit v2; CLAUDE.md rule 10).
    const right =
      c.phase !== null
        ? `<span class="phase-chip phase-chip--${c.phase}">${t("screen_impl.phase_n", { n: c.phase })}</span>`
        : `<small class="aw">${t("screen1.cohort.no_return")}</small>`;
    const dataMark = c.has_data ? "" : `<small class="cohort-row__nodata">${t("common.no_figure")}</small>`;
    row.innerHTML = `<b>${c.name}</b>${dataMark}${right}`;
    row.addEventListener("click", () => navigate({ screen: "country", iso3: c.iso3 }));
    list.appendChild(row);
  }
  return panel;
}
