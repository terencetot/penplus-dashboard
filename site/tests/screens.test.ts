import { describe, expect, it } from "vitest";
import { setLang } from "@/lib/i18n";
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
 * not in a browser during a demo. The assertions are the refinement v2
 * definition of done (docs/refinement/01_AUDIT_REPORT.md): no screen shows
 * "not started" for missing data, no "0 open queries", all 31 countries.
 */
setLang("en");

function container(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

const NOT_STARTED = /not (yet )?started/i;

describe("screens render against the real bundle", () => {
  it("overview: five headline cards, patient totals held by Q-REG-01, all 31 countries", async () => {
    const el = container();
    await renderOverview(el);
    expect(el.textContent).toContain("Regional overview");
    expect(el.querySelectorAll(".coverage-card").length).toBe(5);
    // regional patient totals held: shown as Held with the query, never a number
    const held = el.querySelectorAll(".coverage-card.is-held");
    expect(held.length).toBe(3);
    expect(held[0]!.textContent).toContain("Q-REG-01");
    // "published at least one figure" counts non-null values only
    expect(el.textContent).toContain("17 of 31");
    expect(el.querySelectorAll(".cohort-row").length).toBe(31);
    expect(el.querySelectorAll(".t.p1, .t.p2").length).toBe(31);
    expect(el.querySelectorAll(".milestone-row").length).toBe(5);
    expect(el.textContent).not.toMatch(NOT_STARTED);
  });

  it("indicator detail 2.6: sentinel definition, held Zimbabwe bar, provenance per value", async () => {
    const el = container();
    await renderIndicatorDetail(el, "2.6");
    expect(el.textContent).toContain("Sentinel patients ever enrolled");
    expect(el.textContent).toContain("1 country figure(s) held");
    expect(el.querySelector("#distribution-panel")!.textContent).not.toBe("");
  });

  it("indicator detail 2.6: trend lines only where a real series exists", async () => {
    const el = container();
    await renderIndicatorDetail(el, "2.6");
    const names = Array.from(el.querySelectorAll(".trend-card__name")).map((n) => n.textContent);
    expect(names).toEqual(["Kenya", "Liberia", "Sierra Leone", "Uganda"]);
    expect(el.querySelectorAll(".trend-card .prov--historical").length).toBe(4);
  });

  it("indicator detail 2.6a: Rwanda's active series is drawn", async () => {
    const el = container();
    await renderIndicatorDetail(el, "2.6a");
    const names = Array.from(el.querySelectorAll(".trend-card__name")).map((n) => n.textContent);
    expect(names).toContain("Rwanda");
  });

  it("indicator detail 2.5: counts only countries with a value, lists the rest", async () => {
    const el = container();
    await renderIndicatorDetail(el, "2.5");
    expect(el.textContent).toContain("4 of 31");
    expect(el.querySelectorAll("#distribution-panel .pill").length).toBe(27);
  });

  it("indicator detail: falls back gracefully for an unknown code", async () => {
    const el = container();
    await renderIndicatorDetail(el, "9.9");
    expect(el.querySelector(".callout--empty") || el.querySelector("select")).toBeTruthy();
  });

  it("country profile: phase from the official map, disagreement flagged, figures with source slides", async () => {
    const el = container();
    await renderCountryProfile(el, "GHA");
    expect(el.textContent).toContain("Ghana");
    expect(el.querySelectorAll("#indicator-groups .indicator-group").length).toBe(8);
    expect(el.querySelector(".country-badge")).toBeTruthy();
    expect(el.querySelector(".country-hero .phase-chip")!.textContent).toBe("Phase 4");
    expect(el.querySelector("#implementation-stepper .callout--flag")!.textContent).toContain("phase 3");
    expect(el.querySelectorAll("#implementation-stepper .implementation-stepper__mark").length).toBe(14);
    expect(el.querySelectorAll("#indicator-groups .source-ref").length).toBeGreaterThan(0);
  });

  it("country profile: a second-round country says no return yet, never not started", async () => {
    const el = container();
    await renderCountryProfile(el, "AGO");
    expect(el.textContent).toContain("No return yet");
    expect(el.textContent).not.toMatch(NOT_STARTED);
  });

  it("country profile: queries and facilities from the register", async () => {
    const el = container();
    await renderCountryProfile(el, "ZWE");
    expect(el.querySelectorAll("#queries-list .query-card").length).toBeGreaterThan(0);
    expect(el.textContent).toContain("Q-ZWE-01");
    expect(el.querySelectorAll("#facility-table tbody tr").length).toBe(4);
  });

  it("data quality: all 31 countries, 17 rules, no 'Accepted', no '0 open queries'", async () => {
    const el = container();
    await renderDataQuality(el);
    expect(el.textContent).toContain("Data quality");
    expect(el.querySelectorAll("#provenance-table tbody tr").length).toBe(31);
    expect(el.querySelectorAll("#coverage-matrix tbody tr").length).toBe(31);
    expect(el.querySelectorAll("#coverage-matrix thead th").length).toBe(1 + 16);
    expect(el.querySelectorAll("#checks-table tbody tr").length).toBe(17);
    expect(el.textContent).not.toContain("Accepted");
    expect(el.textContent).not.toMatch(/\b0 open queries/i);
    expect(el.querySelectorAll("#queries-list .query-card").length).toBeGreaterThan(0);
    expect(el.querySelectorAll(".dsa-card").length).toBe(1);
  });

  it("facilities: map points only for checked locations, the rest listed to confirm", async () => {
    const el = container();
    await renderFacilities(el);
    expect(el.querySelector("#facility-map svg")).toBeTruthy();
    expect(el.textContent).toContain("Location to confirm");
    // 28 at their own coordinates, 14 approximate (town), only Chipata off the map (Q-ZMB-02)
    expect(el.querySelectorAll("#to-confirm .pill").length).toBe(1);
    expect(el.querySelector("#to-confirm")!.textContent).toContain("Chipata");
    expect(el.querySelector(".map-disclaimer")!.textContent).toContain("World Health Organization");
    // one button per country with a facility, to zoom the map
    expect(el.querySelectorAll("#map-countries button").length).toBe(15);

    const rowsBefore = el.querySelectorAll("#facility-table tbody tr").length;
    expect(rowsBefore).toBe(25);
    const statusFilter = el.querySelector<HTMLSelectElement>("#status-filter")!;
    statusFilter.value = "planned";
    statusFilter.dispatchEvent(new Event("change"));
    expect(el.querySelectorAll("#facility-table tbody tr").length).toBe(6);
  });

  it("implementation phases: 1 / 15 / 3 / 1 + 11 no return, no 'not started'", async () => {
    const el = container();
    await renderImplementation(el);
    expect(el.textContent).toContain("Implementation phases");
    expect(el.querySelector("#phase-summary-panel")!.textContent).not.toBe("");
    const table = el.querySelector("#implementation-table")!;
    expect(table.querySelectorAll("tbody tr").length).toBe(31);
    expect(table.querySelectorAll(".phase-grid__noreturn").length).toBe(11);
    expect(table.querySelectorAll(".flag-mark").length).toBe(5);
    expect(el.textContent).not.toMatch(NOT_STARTED);
  });
});
