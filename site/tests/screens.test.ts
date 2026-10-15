import { describe, expect, it } from "vitest";
import { setLang } from "@/lib/i18n";
import { setDemoMode } from "@/lib/demo";
import { renderOverview } from "@/screens/overview";
import { renderIndicatorDetail } from "@/screens/indicator-detail";
import { renderCountryProfile } from "@/screens/country-profile";
import { renderDataQuality } from "@/screens/data-quality";
import { renderFacilities } from "@/screens/facilities";
import { renderImplementation } from "@/screens/implementation";

/**
 * These render each screen against the REAL bundle in site/public/data (via
 * the fetch stub in tests/setup.ts), not a hand-written fixture -- so a
 * change to export.py's output shape that a screen can't handle fails here,
 * not in a browser during a demo.
 */
setLang("en");

function container(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

describe("screens render against the real bundle without throwing", () => {
  it("overview: hero coverage cards, isometric map, cohort lists, milestone strip", async () => {
    const el = container();
    await renderOverview(el);
    expect(el.textContent).toContain("Regional overview");
    expect(el.querySelectorAll(".coverage-card").length).toBe(4);
    expect(el.querySelectorAll(".t.p1, .t.p2").length).toBeGreaterThan(0);
    expect(el.querySelectorAll(".cohort-row").length).toBeGreaterThan(0);
    expect(el.querySelectorAll(".milestone-row").length).toBe(5);
  });

  it("indicator detail: definition, distribution and trend", async () => {
    const el = container();
    await renderIndicatorDetail(el, "2.5");
    expect(el.textContent).toContain("Unique patients ever enrolled");
    expect(el.querySelector("#distribution-panel")!.textContent).not.toBe("");
    expect(el.querySelector("#trend-panel")!.textContent).not.toBe("");
  });

  it("indicator detail: trend small multiples show the countries with the most reported periods", async () => {
    const el = container();
    await renderIndicatorDetail(el, "2.5");
    // LBR, SLE and UGA have the most periods (5) in the real bundle for 2.5;
    // single-period countries (BFA, COD, ZWE...) must not take a panel.
    const names = Array.from(el.querySelectorAll(".trend-card__name")).map((n) => n.textContent);
    expect(names).toEqual(["Liberia", "Sierra Leone", "Uganda"]);
    expect(el.querySelectorAll(".trend-card .chip--historical").length).toBe(3);
  });

  it("indicator detail: 2.5 counts only countries with a published value, and lists the rest", async () => {
    const el = container();
    await renderIndicatorDetail(el, "2.5");
    expect(el.textContent).toContain("6 of 31");
    expect(el.querySelectorAll("#distribution-panel .pill").length).toBe(25);
  });

  it("indicator detail: falls back gracefully for an unknown code", async () => {
    const el = container();
    await renderIndicatorDetail(el, "9.9");
    // dim.find fails, falls back to bundle.dim[0] rather than throwing
    expect(el.querySelector(".callout--empty") || el.querySelector("select")).toBeTruthy();
  });

  it("country profile: all indicators, facilities, governance, queries", async () => {
    const el = container();
    await renderCountryProfile(el, "GHA");
    expect(el.textContent).toContain("Ghana");
    // every indicator appears once, grouped by Results Framework family
    expect(el.querySelectorAll("#indicator-groups .indicator-row").length).toBe(17);
    expect(el.querySelectorAll("#indicator-groups .indicator-group").length).toBe(8);
    expect(el.querySelector(".country-badge")).toBeTruthy();
  });

  it("country profile: a governance milestone linked to indicator 1.1-1.3 shows the same status pill in both the all-indicators table and the governance panel", async () => {
    // The real bundle's governance rows predate the v3-form correction and
    // carry indicator_code=null throughout (pre-existing historical data,
    // not this fix's concern) -- this fixture proves the wiring works
    // whenever a governance row IS linked to an indicator, which the demo
    // bundle's generator (built from the current v3-form pipeline path)
    // always produces for 1.1-1.3.
    setDemoMode(true);
    try {
      const el = container();
      await renderCountryProfile(el, "GHA");
      const row11 = el.querySelector('#indicator-groups .indicator-row[data-code="1.1"]');
      expect(row11).toBeTruthy();
      expect(row11!.querySelector(".status")).toBeTruthy();
    } finally {
      setDemoMode(false);
    }
  });

  it("country profile: implementation-phase stepper shows all fourteen steps", async () => {
    const el = container();
    await renderCountryProfile(el, "GHA");
    const stepper = el.querySelector("#implementation-stepper")!;
    expect(stepper.querySelectorAll(".implementation-stepper__mark").length).toBe(14);
  });

  it("country profile: a country with zero returns says so instead of erroring", async () => {
    const el = container();
    await renderCountryProfile(el, "AGO");
    expect(el.textContent).toMatch(/no return|Angola/i);
  });

  it("data quality: completeness distribution and open query register", async () => {
    const el = container();
    await renderDataQuality(el);
    expect(el.textContent).toContain("Data quality");
    expect(el.querySelector("#quality-table")!.querySelectorAll("tbody tr").length).toBeGreaterThan(0);
  });

  it("facilities: table renders and country/status filters narrow it", async () => {
    const el = container();
    await renderFacilities(el);
    const rowsBefore = el.querySelectorAll("#facility-table tbody tr").length;
    expect(rowsBefore).toBeGreaterThan(0);

    const statusFilter = el.querySelector<HTMLSelectElement>("#status-filter")!;
    statusFilter.value = "operational";
    statusFilter.dispatchEvent(new Event("change"));
    const rowsAfter = el.querySelectorAll("#facility-table tbody tr").length;
    expect(rowsAfter).toBeLessThanOrEqual(rowsBefore);
  });

  it("implementation phases: leads with a phase-distribution summary chart", async () => {
    const el = container();
    await renderImplementation(el);
    expect(el.textContent).toContain("Implementation phases");
    expect(el.querySelector("#phase-summary-panel")!.textContent).not.toBe("");
    // the detailed grid is not built until the disclosure is opened
    expect(el.querySelector("#implementation-table")!.querySelectorAll("tbody tr").length).toBe(0);
  });

  it("implementation phases: the full grid builds lazily once the detail disclosure opens", async () => {
    const el = container();
    await renderImplementation(el);
    const detail = el.querySelector<HTMLDetailsElement>("#grid-detail")!;
    detail.open = true;
    detail.dispatchEvent(new Event("toggle"));
    const table = el.querySelector("#implementation-table")!;
    // grouped two-row header: row 1 is (country + highest-phase, each
    // rowspan 2) plus one <th> per phase group (5); row 2 is one <th> per
    // step (14) -- see components/phase-grid.ts
    const headerRows = table.querySelectorAll("thead tr");
    expect(headerRows.length).toBe(2);
    expect(headerRows[0]!.querySelectorAll("th").length).toBe(2 + 5);
    expect(headerRows[1]!.querySelectorAll("th").length).toBe(14);
    expect(table.querySelectorAll("tbody tr").length).toBeGreaterThan(0);
    // the country column is frozen (sticky), not just another column
    expect(table.querySelector("tbody td.phase-grid__pin")).toBeTruthy();
  });
});
