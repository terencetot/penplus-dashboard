import { describe, expect, it } from "vitest";
import { renderStatus, statusFromGovernance } from "@/lib/status";
import { verdictKey } from "@/lib/vocab";

// Non-negotiable rule 10 (CLAUDE.md): "A country on hold is shown as awaiting
// clarification, never as zero and never omitted." A return's verdict is not
// a milestone judgment, so accepted/query get their own labels rather than
// being stretched into the met/partly-met/not-met vocabulary (see vocab.ts).
describe("verdictKey", () => {
  it("gives accepted and query their own labels, not the milestone vocabulary", () => {
    expect(verdictKey("accepted")).toBe("verdict.accepted");
    expect(verdictKey("query")).toBe("verdict.query");
  });
});

// Data model rule (2_Fields, fact_governance / dim_governance note):
// "A Yes without a document title is not counted."
describe("statusFromGovernance", () => {
  it("does not count a Yes with no document", () => {
    expect(statusFromGovernance("yes", false)).toBe("not_met");
  });
  it("counts a Yes with a document as met", () => {
    expect(statusFromGovernance("yes", true)).toBe("met");
  });
  it("treats under_development as partly_met, no as not_met, else not_reported", () => {
    expect(statusFromGovernance("under_development", false)).toBe("partly_met");
    expect(statusFromGovernance("no", false)).toBe("not_met");
    expect(statusFromGovernance(null, false)).toBe("not_reported");
  });
});

// Display rule 8: "Colour never carries meaning alone" -- every status mark
// must render with a text label, not a bare colour swatch.
describe("renderStatus", () => {
  it("always pairs the mark with a text label", () => {
    const html = renderStatus("met", "Met");
    expect(html).toContain("Met");
    expect(html).toContain("status--met");
  });
});
