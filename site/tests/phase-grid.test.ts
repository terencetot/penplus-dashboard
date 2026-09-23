import { describe, expect, it } from "vitest";
import { buildPhaseGrid } from "@/components/phase-grid";
import type { ImplementationCountry, ImplementationStepDim } from "@/lib/types";

const steps: ImplementationStepDim[] = [
  { step_no: 1, phase_no: 1, phase_label: "Phase 1. Assessment", step_label: "Assess" },
  { step_no: 2, phase_no: 1, phase_label: "Phase 1. Assessment", step_label: "SWOT" },
  { step_no: 3, phase_no: 2, phase_label: "Phase 2. Service delivery model", step_label: "Design" },
];

function makeCountry(iso3: string, statuses: (string | null)[]): ImplementationCountry {
  return {
    iso3,
    name: iso3,
    highest_phase_completed: 1,
    steps: steps.map((s, i) => ({
      step_no: s.step_no,
      status: statuses[i] as ImplementationCountry["steps"][number]["status"],
      source: null,
      as_of: null,
    })),
  };
}

describe("buildPhaseGrid", () => {
  it("groups the header into a phase row (colspans summing to the step count) and a step-number row", () => {
    const el = buildPhaseGrid("test", steps, [makeCountry("GHA", ["yes", "yes", "no"])]);
    const headerRows = el.querySelectorAll("thead tr");
    expect(headerRows.length).toBe(2);

    const phaseHeaders = Array.from(headerRows[0]!.querySelectorAll("th.phase-grid__phase-band"));
    const totalSpan = phaseHeaders.reduce((sum, th) => sum + Number((th as HTMLTableCellElement).colSpan), 0);
    expect(totalSpan).toBe(steps.length);

    const stepHeaders = headerRows[1]!.querySelectorAll("th");
    expect(Array.from(stepHeaders).map((th) => th.textContent)).toEqual(["1", "2", "3"]);
  });

  it("marks the last column of each phase group so the grouping is visible structurally, not only by tint", () => {
    const el = buildPhaseGrid("test", steps, [makeCountry("GHA", ["yes", "yes", "no"])]);
    const stepHeaders = Array.from(el.querySelectorAll("thead tr")[1]!.querySelectorAll("th"));
    // step 2 is the last of phase 1 (steps 1-2), step 3 is the last (only) of phase 2
    expect(stepHeaders[0]!.classList.contains("phase-grid__band-end")).toBe(false);
    expect(stepHeaders[1]!.classList.contains("phase-grid__band-end")).toBe(true);
    expect(stepHeaders[2]!.classList.contains("phase-grid__band-end")).toBe(true);
  });

  it("freezes the country column (sticky) in both header and body", () => {
    const el = buildPhaseGrid("test", steps, [makeCountry("GHA", ["yes", "yes", "no"])]);
    expect(el.querySelector("thead th.phase-grid__pin")).toBeTruthy();
    const bodyPin = el.querySelector("tbody td.phase-grid__pin")!;
    expect(bodyPin.textContent).toBe("GHA");
  });

  it("paginates and updates the visible rows when Next is clicked", () => {
    const countries = Array.from({ length: 25 }, (_, i) =>
      makeCountry(`C${i.toString().padStart(2, "0")}`, ["yes", "no", null]),
    );
    const el = buildPhaseGrid("test", steps, countries, 20);
    expect(el.querySelectorAll("tbody tr").length).toBe(20);

    const next = Array.from(el.querySelectorAll<HTMLButtonElement>(".pager button")).find(
      (b) => !b.disabled,
    )!;
    next.click();
    expect(el.querySelectorAll("tbody tr").length).toBe(5);
  });
});
