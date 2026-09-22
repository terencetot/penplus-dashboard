import { describe, expect, it } from "vitest";
import { gapText } from "@/components/milestone-strip";

// A positive gap is a shortfall, a negative gap is over-achievement.
// `Math.abs(gap)` used to erase that sign: a regional value of 306 against a
// milestone of 120 (gap = 120 - 306 = -186) rendered "Gap to milestone: 186"
// instead of "Milestone exceeded by 186".
describe("gapText", () => {
  it("reads a positive gap as a shortfall", () => {
    expect(gapText(186)).toBe("Gap to milestone: 186");
  });

  it("reads a negative gap as over-achievement, not a shortfall", () => {
    expect(gapText(-186)).toBe("Milestone exceeded by: 186");
    expect(gapText(-186)).not.toContain("Gap to milestone");
  });

  it("reads a zero gap as met", () => {
    expect(gapText(0)).toBe("Milestone met");
  });

  it("falls back to the no-milestone text when the gap is null", () => {
    expect(gapText(null)).toBe("Milestone not yet published");
  });
});
