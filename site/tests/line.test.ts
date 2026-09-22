import { describe, expect, it } from "vitest";
import { lineTrend, type TrendPoint } from "@/charts/line";

// A cohort/funding-round boundary must actually break the drawn line, not
// just get a dashed rule drawn on top of an unbroken join -- Plot.lineY only
// breaks where y is null/NaN, so a boundary between two real, adjacent
// points needs its own z channel (charts/line.ts).
describe("lineTrend series break", () => {
  const points: TrendPoint[] = [
    { period_id: "2025-Q4", value: 10, series: "GHA" },
    { period_id: "2026-Q1", value: 20, series: "GHA" },
    { period_id: "2026-Q2", value: 30, series: "GHA" },
  ];

  it("draws one continuous path per series when there is no break", () => {
    const svg = lineTrend(points, { valueLabel: "value" }) as SVGElement;
    const linePaths = svg.querySelectorAll('g[aria-label="line"] path');
    expect(linePaths.length).toBe(1);
  });

  it("draws two separate path segments when a series break falls between two real points", () => {
    const svg = lineTrend(points, {
      valueLabel: "value",
      seriesBreakAt: "2026-Q1",
      seriesBreakLabel: "Funding round 1 → 2",
    }) as SVGElement;
    const linePaths = svg.querySelectorAll('g[aria-label="line"] path');
    expect(linePaths.length).toBe(2);
  });
});
