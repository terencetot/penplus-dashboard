import { describe, expect, it } from "vitest";
import { renderValueWithCompleteness } from "@/components/completeness";

// Display rule 4: "Completeness travels with the figure. Below 80 per cent
// the value renders in a muted state with the share visible without
// interaction" -- applies to every country-level figure, not only the
// dedicated completeness column (data-quality screen).
describe("renderValueWithCompleteness", () => {
  it("leaves a well-completed figure untouched", () => {
    expect(renderValueWithCompleteness("120", 0.95)).toBe("120");
  });

  it("mutes a figure below 80% completeness and shows the share inline", () => {
    const html = renderValueWithCompleteness("120", 0.6);
    expect(html).toContain("120");
    expect(html).toContain("is-low");
    expect(html).toContain("60%");
  });

  it("leaves a figure untouched when completeness itself was not reported", () => {
    // isLowCompleteness(null) is false by design (lib/format.ts): a missing
    // completeness figure is a distinct unknown state, not assumed low.
    expect(renderValueWithCompleteness("120", null)).toBe("120");
  });
});
