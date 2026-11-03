import { describe, expect, it } from "vitest";
import { setLang } from "@/lib/i18n";
import { renderOverview } from "@/screens/overview";
import { renderIndicatorDetail } from "@/screens/indicator-detail";
import { renderCountryProfile } from "@/screens/country-profile";
import { renderDataQuality } from "@/screens/data-quality";
import { renderFacilities } from "@/screens/facilities";
import { renderImplementation } from "@/screens/implementation";

/**
 * Every screen renders against the REAL bundle in site/public/data (via the
 * fetch stub in tests/setup.ts), so a change to export.py's output that a
 * screen cannot handle fails here. The assertions are the director edition's
 * promises (docs/review/REVUE_DASHBOARD.md): real figures, all 31 countries,
 * no "not started" for missing data, no source branding, no demo mode.
 */
function container(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

const NOT_STARTED = /not (yet )?started|non commenc/i;
const BRANDING = /ICPPA|\bdemo\b|démonstration/i;

describe("screens render against the real bundle", () => {
  it("overview: programme figures, all 31 countries, no held totals", async () => {
    setLang("en");
    const el = container();
    await renderOverview(el);
    expect(el.textContent).toContain("PEN-Plus in Africa");
    expect(el.querySelectorAll(".stat").length).toBe(5);
    // programme figures (data/reference/programme_figures.csv), no coverage line on the cards
    expect(el.textContent).toContain("Reporting facilities");
    expect(el.textContent).toContain("+170,000");
    expect(el.textContent).toContain("+17,500");
    expect(el.querySelector(".kpi-band")!.textContent).not.toMatch(/countries reporting/);
    expect(el.querySelectorAll("#situation-body tr").length).toBe(31);
    // Zimbabwe published as reported (Q-ZWE-01 closed by programme decision)
    expect(el.querySelector("#situation-body tr[data-iso3='ZWE']")!.textContent).not.toContain("to verify");
    expect(el.textContent).not.toMatch(/Held/);
    expect(el.textContent).not.toMatch(NOT_STARTED);
    expect(el.textContent).not.toMatch(BRANDING);
  });

  it("overview: the round filter narrows the table", async () => {
    setLang("en");
    const el = container();
    await renderOverview(el);
    el.querySelector<HTMLButtonElement>('#round-filter button[data-round="phase_2"]')!.click();
    expect(el.querySelectorAll("#situation-body tr").length).toBe(11);
  });

  it("indicator detail 2.6: regional value, by country, by condition, trends", async () => {
    setLang("en");
    const el = container();
    await renderIndicatorDetail(el, "2.6");
    expect(el.textContent).toContain("+170,000");
    expect(el.querySelector("#distribution-panel")!.textContent).not.toBe("");
    expect(el.querySelector("#condition-panel")!.textContent).toContain("By condition");
    const names = Array.from(el.querySelectorAll(".trend-card__name")).map((n) => n.textContent);
    expect(names).toEqual(["Kenya", "Liberia", "Sierra Leone", "Uganda"]);
    expect(el.textContent).not.toMatch(BRANDING);
  });

  it("indicator detail: indicators with data are listed first", async () => {
    setLang("en");
    const el = container();
    await renderIndicatorDetail(el, "2.6");
    const groups = el.querySelectorAll("#indicator-select optgroup");
    expect(groups[0]!.getAttribute("label")).toBe("With data");
  });

  it("indicator detail: falls back gracefully for an unknown code", async () => {
    setLang("en");
    const el = container();
    await renderIndicatorDetail(el, "9.9");
    expect(el.querySelector(".callout--empty") || el.querySelector("select")).toBeTruthy();
  });

  it("in French: country and indicator names are translated", async () => {
    setLang("fr");
    const el = container();
    await renderIndicatorDetail(el, "2.6");
    expect(el.textContent).toContain("République démocratique du Congo");
    expect(el.textContent).toContain("drépanocytose");
    expect(el.textContent).not.toContain("Democratic Republic of the Congo");
    setLang("en");
  });

  it("country profile: header, figures, reported indicators, steps", async () => {
    setLang("en");
    const el = container();
    await renderCountryProfile(el, "SLE");
    expect(el.querySelector(".cprofile h1")!.textContent).toBe("Sierra Leone");
    expect(el.querySelectorAll(".cprofile__fig").length).toBe(4);
    expect(el.querySelectorAll(".ind-tile").length).toBeGreaterThan(0);
    expect(el.querySelectorAll("#implementation-stepper .implementation-stepper__mark").length).toBe(14);
    expect(el.querySelectorAll("#facility-table tbody tr").length).toBe(4);
    expect(el.textContent).not.toMatch(BRANDING);
  });

  it("country profile: a second-round country says no data yet, never not started", async () => {
    setLang("en");
    const el = container();
    await renderCountryProfile(el, "AGO");
    expect(el.textContent).toContain("No data yet");
    expect(el.textContent).not.toMatch(NOT_STARTED);
  });

  it("implementation: no map, 1 in phase 5 and 17 in phase 4, official phase wording", async () => {
    setLang("en");
    const el = container();
    await renderImplementation(el);
    expect(el.querySelector(".phase-map-panel")).toBeNull();
    expect(el.textContent).not.toContain("Where each country stands");
    const kpis = Array.from(el.querySelectorAll(".stat__value")).map((e) => e.textContent);
    expect(kpis.slice(1, 3)).toEqual(["1", "17"]);
    expect(el.textContent).toContain("Phase 1. Assessment of the system and of facility readiness");
    expect(el.textContent).toContain(
      "Conduct a comprehensive assessment of existing health care and facilities",
    );
    const table = el.querySelector("#implementation-table")!;
    expect(table.querySelectorAll("tbody tr").length).toBe(31);
    expect(table.querySelectorAll(".phase-grid__noreturn").length).toBe(11);
    expect(el.textContent).not.toMatch(NOT_STARTED);
  });

  it("data quality: all 31 countries, 16 indicators, 17 rules, no 'Accepted'", async () => {
    setLang("en");
    const el = container();
    await renderDataQuality(el);
    expect(el.querySelectorAll("#provenance-table tbody tr").length).toBe(31);
    expect(el.querySelectorAll("#coverage-matrix tbody tr").length).toBe(31);
    expect(el.querySelectorAll("#coverage-matrix thead th").length).toBe(1 + 16);
    expect(el.querySelectorAll("#checks-table tbody tr").length).toBe(17);
    expect(el.textContent).not.toContain("Accepted");
    expect(el.querySelectorAll("#queries-list .query-card").length).toBeGreaterThan(0);
  });

  it("facilities: atlas with one point per facility, no 'approximate' wording", async () => {
    setLang("en");
    const el = container();
    await renderFacilities(el);
    expect(el.querySelector("#facility-map svg")).toBeTruthy();
    expect(el.querySelectorAll("#map-countries button").length).toBe(15);
    // WHO's standard disclaimer speaks of "approximate border lines"; nothing else may
    expect(el.querySelector("#facility-map")!.textContent).not.toMatch(/approximate/i);
    expect(el.querySelector("#facility-table")!.textContent).not.toMatch(/approximate/i);
    expect(el.textContent).not.toMatch(BRANDING);
    // a click on a facility point opens its card
    el.querySelector<SVGElement>("#map-canvas g.fm-exact > *")!.dispatchEvent(new Event("click"));
    expect(el.querySelector<HTMLElement>("#map-card")!.hidden).toBe(false);
    // filters narrow the register
    const statusFilter = el.querySelector<HTMLSelectElement>("#status-filter")!;
    statusFilter.value = "planned";
    statusFilter.dispatchEvent(new Event("change"));
    expect(el.querySelectorAll("#facility-table tbody tr").length).toBe(6);
  });
});
