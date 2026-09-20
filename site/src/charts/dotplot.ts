import * as Plot from "@observablehq/plot";

export interface DotDatum {
  label: string;
  value: number;
  group?: string;
}

/**
 * Dot plots for distribution (CLAUDE.md, Charts). Used where a value should
 * be read as a spread along one axis without the sorted-ranking implication
 * a bar chart carries -- e.g. completeness across countries on screen 4.
 */
export function dotPlot(
  data: DotDatum[],
  opts: { valueLabel: string; groupColors?: Record<string, string> },
): SVGElement | HTMLElement {
  return Plot.plot({
    height: 140,
    marginLeft: 20,
    x: { label: opts.valueLabel, grid: true, nice: true },
    y: { axis: null },
    marks: [
      Plot.dotX(data, {
        x: "value",
        fill: opts.groupColors
          ? (d: DotDatum) => opts.groupColors![d.group ?? ""] ?? "var(--color-primary)"
          : "var(--color-primary)",
        r: 5,
        fillOpacity: 0.85,
        tip: true,
        title: (d: DotDatum) => `${d.label}: ${d.value}`,
      }),
      Plot.ruleX([0]),
    ],
  });
}
