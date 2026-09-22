import { describe, expect, it } from "vitest";
import { horizontalBars, type BarDatum } from "@/charts/bar";

// CLAUDE.md rule 7: "Suppress numerators below five... and flag the
// suppression rather than blanking silently." A suppressed country's real
// number is withheld by the pipeline (value: null), but the bar itself must
// still appear -- disappearing from the chart would read as "never
// reported," which is a different, false claim.
describe("horizontalBars suppression", () => {
  it("still draws a bar for a suppressed row with a null value", () => {
    const data: BarDatum[] = [
      { label: "GHA", value: 40, title: "GHA: 40" },
      { label: "KEN", value: null, suppressed: true, title: "KEN: suppressed" },
    ];
    const svg = horizontalBars(data, { valueLabel: "patients" }) as SVGElement;
    const bars = svg.querySelectorAll('g[aria-label="bar"] rect');
    expect(bars.length).toBe(2);
  });

  it("does not throw when every row is suppressed", () => {
    const data: BarDatum[] = [{ label: "KEN", value: null, suppressed: true }];
    expect(() => horizontalBars(data, { valueLabel: "patients" })).not.toThrow();
  });
});
