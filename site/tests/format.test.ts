import { describe, expect, it } from "vitest";
import { fmtCount, fmtNandN, fmtRateWithNandN, isLowCompleteness, isSmallN, NR } from "@/lib/format";

// Rule 2 (CLAUDE.md): "Null is not zero." Every formatter must return the
// explicit NR marker for null/undefined, never "0" and never "".
describe("fmtCount", () => {
  it("renders null as NR, never 0", () => {
    expect(fmtCount(null)).toBe(NR);
    expect(fmtCount(undefined)).toBe(NR);
  });
  it("renders a genuine zero as 0", () => {
    expect(fmtCount(0)).toBe("0");
  });
  it("formats a count with thousands separators", () => {
    expect(fmtCount(13222)).toBe("13,222");
  });
});

describe("fmtRateWithNandN / display rule 1", () => {
  it("never shows a rate without n and N", () => {
    expect(fmtRateWithNandN(null, 100, 0.5)).toBe(NR);
    expect(fmtRateWithNandN(50, null, 0.5)).toBe(NR);
    expect(fmtRateWithNandN(50, 100, null)).toBe(NR);
  });
  it("shows the rate with both parts when complete", () => {
    expect(fmtRateWithNandN(50, 100, 0.5)).toBe("50% (n=50 of N=100)");
  });
});

describe("fmtNandN", () => {
  it("is NR if either part is missing", () => {
    expect(fmtNandN(null, 10)).toBe(NR);
    expect(fmtNandN(10, null)).toBe(NR);
  });
});

describe("isLowCompleteness / display rule 4", () => {
  it("is low below 80%, not at or above it", () => {
    expect(isLowCompleteness(0.79)).toBe(true);
    expect(isLowCompleteness(0.8)).toBe(false);
    expect(isLowCompleteness(null)).toBe(false); // absence is a different state, not "low"
  });
});

describe("isSmallN / specification rule 1 (confidence interval below 20)", () => {
  it("flags a denominator under twenty", () => {
    expect(isSmallN(19)).toBe(true);
    expect(isSmallN(20)).toBe(false);
    expect(isSmallN(null)).toBe(false);
  });
});
