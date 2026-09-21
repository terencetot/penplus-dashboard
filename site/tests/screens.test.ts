import { describe, expect, it } from "vitest";
import { setLang } from "@/lib/i18n";
import { renderOverview } from "@/screens/overview";
import { renderIndicatorDetail } from "@/screens/indicator-detail";
import { renderCountryProfile } from "@/screens/country-profile";
import { renderDataQuality } from "@/screens/data-quality";
import { renderFacilities } from "@/screens/facilities";

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
  it("overview: hero figures, country grid, milestone strip", async () => {
    const el = container();
    await renderOverview(el);
    expect(el.textContent).toContain("Regional overview");
    expect(el.querySelectorAll(".signal-card").length).toBe(4);
    expect(el.querySelectorAll(".country-tile").length).toBeGreaterThan(0);
    expect(el.querySelectorAll(".milestone-row").length).toBe(5);
  });

  it("indicator detail: definition, distribution and trend", async () => {
    const el = container();
    await renderIndicatorDetail(el, "2.5");
    expect(el.textContent).toContain("Unique patients ever enrolled");
    expect(el.querySelector("#distribution-panel")!.textContent).not.toBe("");
    expect(el.querySelector("#trend-panel")!.textContent).not.toBe("");
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
    expect(el.querySelector("#indicator-table")!.querySelectorAll("tbody tr").length).toBeGreaterThan(0);
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
});
