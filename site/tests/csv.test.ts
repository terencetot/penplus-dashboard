import { describe, expect, it } from "vitest";
import { toCSV } from "@/components/csv";

describe("toCSV", () => {
  it("quotes fields containing commas, quotes or newlines", () => {
    const csv = toCSV(["a", "b"], [["x,y", 'has "quotes"']]);
    expect(csv).toContain('"x,y"');
    expect(csv).toContain('"has ""quotes"""');
  });

  it("writes NR as the literal text, never as an empty cell or 0", () => {
    const csv = toCSV(["value"], [["NR"]]);
    expect(csv.split("\r\n")[1]).toBe("NR");
  });
});
