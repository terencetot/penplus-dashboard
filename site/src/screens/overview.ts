import { getFacilities, getOverview } from "@/lib/bundle";
import { fmtCount } from "@/lib/format";
import { t } from "@/lib/i18n";
import { navigate } from "@/router";
import { loadWhoGeo, renderHeroMap } from "@/components/facility-map";
import type { OverviewBundle, RegionalFigure } from "@/lib/types";

type Row = OverviewBundle["country_table"][number];

/**
 * Screen 1: "Where is PEN-Plus and how big is it?" A dark hero with the real
 * map (WHO boundaries, countries tinted by HCT round, one point per facility),
 * five headline figures, then the situation country by country. Every total,
 * coverage and bar length comes from export.py; rows are alphabetical, never
 * a ranking (CLAUDE.md rule 5).
 */
export async function renderOverview(container: HTMLElement): Promise<void> {
  container.innerHTML = `<p class="skeleton" style="height:280px"></p>`;
  const [bundle, facilities, geo] = await Promise.all([getOverview(), getFacilities(), loadWhoGeo()]);
  const h = bundle.headline;
  const p = bundle.programme;

  container.innerHTML = `
    <section class="hero hero--atlas">
      <div class="hero__grid">
        <div class="hero__text">
          <span class="hero__eyebrow">${t("screen1.eyebrow")}</span>
          <h1>${t("screen1.title")}</h1>
          <p class="q">${t("screen1.question")}</p>
          <p class="sum">${t("screen1.summary_v3", {
            countries: p.countries,
            round1: p.round1,
            round2: p.round2,
            facilities: fmtCount(h.facilities.total),
            patients: fmtCount(h.sentinel_ever.total),
            reporting: h.sentinel_ever.countries_reporting,
          })}</p>
          <div class="leg">
            <span><i class="a"></i>${t("screen1.hero.phase1_legend", { n: p.round1 })}</span>
            <span><i class="b"></i>${t("screen1.hero.phase2_legend", { n: p.round2 })}</span>
            <span><i class="dot"></i>${t("screen1.hero.facility_legend")}</span>
          </div>
        </div>
        <div class="hero__map" id="hero-map"></div>
      </div>
    </section>

    <div class="kpi-band">
      <div class="stat-row">
        ${stat(t("screen1.kpi.countries"), fmtCount(p.countries), t("screen1.kpi.countries_sub", { r1: p.round1, r2: p.round2 }))}
        ${figure(t("screen1.kpi.facilities"), h.facilities, t("screen1.kpi.facilities_sub"))}
        ${figure(t("screen1.kpi.patients"), h.sentinel_ever, t("screen1.kpi.patients_sub"))}
        ${figure(t("screen1.kpi.trained"), h.trained, t("screen1.kpi.trained_sub"))}
        ${stat(t("screen1.kpi.phase"), `${p.phase45}<small>/${p.with_phase}</small>`, t("screen1.kpi.phase_sub"))}
      </div>
    </div>

    <section class="panel situation">
      <div class="situation__head">
        <div>
          <h3 class="panel__title">${t("screen1.table.title")}</h3>
          <p class="panel__question">${t("screen1.table.caption")}</p>
        </div>
        <div class="seg" role="tablist" id="round-filter">
          <button type="button" class="is-active" data-round="">${t("common.all")}</button>
          <button type="button" data-round="phase_1">${t("common.phase1")}</button>
          <button type="button" data-round="phase_2">${t("common.phase2")}</button>
        </div>
      </div>
      <div class="data-table-wrap">
        <table class="situation__table">
          <caption class="sr-only">${t("screen1.table.title")}</caption>
          <thead><tr>
            <th scope="col">${t("common.select_country")}</th>
            <th scope="col">${t("table.cohort")}</th>
            <th scope="col">${t("screen_impl.column.phase")}</th>
            <th scope="col" class="num">${t("screen1.table.facilities")}</th>
            <th scope="col" class="num">${t("screen1.table.patients")}</th>
            <th scope="col" class="num">${t("screen1.table.trained")}</th>
          </tr></thead>
          <tbody id="situation-body"></tbody>
        </table>
      </div>
      <p class="chart-caption">${t("screen1.table.footnote")}</p>
    </section>
  `;

  container.querySelector("#hero-map")!.appendChild(renderHeroMap(geo, facilities.rows));

  const body = container.querySelector<HTMLElement>("#situation-body")!;
  const draw = (round: string) => {
    body.innerHTML = bundle.country_table
      .filter((r) => !round || r.cohort === round)
      .map(rowHtml)
      .join("");
    body
      .querySelectorAll<HTMLTableRowElement>("tr[data-iso3]")
      .forEach((tr) =>
        tr.addEventListener("click", () => navigate({ screen: "country", iso3: tr.dataset.iso3! })),
      );
  };
  const seg = container.querySelectorAll<HTMLButtonElement>("#round-filter button");
  seg.forEach((b) =>
    b.addEventListener("click", () => {
      seg.forEach((x) => x.classList.toggle("is-active", x === b));
      draw(b.dataset.round ?? "");
    }),
  );
  draw("");
}

function stat(label: string, value: string, sub: string): string {
  return `<div class="stat"><span class="stat__label">${label}</span>
    <b class="stat__value num">${value}</b><span class="stat__sub">${sub}</span></div>`;
}

/** A regional total with its country coverage, written and drawn (31 pips). */
function figure(label: string, f: RegionalFigure, sub: string): string {
  const partial = f.coverage_pct !== null && f.coverage_pct < 80;
  const pips = Array.from(
    { length: f.countries_total },
    (_, i) => `<i class="${i < f.countries_reporting ? "f" : ""}"></i>`,
  ).join("");
  return `<div class="stat${partial ? " is-partial" : ""}"><span class="stat__label">${label}</span>
    <b class="stat__value num">${f.total === null ? "—" : fmtCount(f.total)}</b>
    <span class="stat__sub">${sub}</span>
    <span class="stat__cov">${t("screen1.kpi.coverage", { n: f.countries_reporting, total: f.countries_total })}</span>
    <span class="stat__pips" aria-hidden="true">${pips}</span></div>`;
}

function bar(value: number | null, pct: number | null, extra = ""): string {
  if (value === null) return `<span class="cell-empty">—</span>`;
  return `<span class="cell-bar"><span class="cell-bar__v num">${fmtCount(value)}${extra}</span>${
    pct !== null ? `<span class="cell-bar__track"><span style="width:${pct}%"></span></span>` : ""
  }</span>`;
}

function rowHtml(r: Row): string {
  const phase =
    r.phase !== null
      ? `<span class="phase-chip phase-chip--${r.phase}">${t("screen_impl.phase_n", { n: r.phase })}</span>`
      : `<span class="muted-chip">${t("screen1.table.no_data")}</span>`;
  let patients: string;
  if (r.patients !== null) {
    patients = r.patients_held
      ? `<span class="cell-bar"><span class="cell-bar__v num">${fmtCount(r.patients)}</span><span class="tag-check">${t("screen1.table.to_check")}</span></span>`
      : bar(r.patients, r.patients_bar);
  } else if (r.patients_all !== null) {
    patients = bar(r.patients_all, null, ` <small>${t("screen1.table.all_conditions")}</small>`);
  } else if (r.patients_active !== null) {
    patients = bar(r.patients_active, null, ` <small>${t("screen1.table.in_care")}</small>`);
  } else {
    patients = `<span class="cell-empty">—</span>`;
  }
  return `<tr data-iso3="${r.iso3}" tabindex="0">
    <th scope="row"><span class="ctry"><span class="ctry__iso">${r.iso3}</span>${r.name}</span></th>
    <td><span class="round round--${r.cohort}">${t(r.cohort === "phase_1" ? "screen1.table.round1" : "screen1.table.round2")}</span></td>
    <td>${phase}</td>
    <td class="num">${bar(r.facilities, r.facilities_bar)}</td>
    <td class="num">${patients}</td>
    <td class="num">${bar(r.trained, r.trained_bar)}</td>
  </tr>`;
}
