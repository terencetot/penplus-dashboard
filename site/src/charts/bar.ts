import * as Plot from "@observablehq/plot";
import { emptyChart } from "./empty";

export interface BarDatum {
  label: string;
  value: number;
  /** true when this bar represents a small, suppressed cell (rendered muted + hatched). */
  suppressed?: boolean;
  /** shown on hover -- display rule 1: never a rate without n and N. */
  title?: string;
}

/**
 * Horizontal bars for comparison across countries (CLAUDE.md, Charts: "Horizontal
 * bars for comparison across countries... Not allowed: pie charts, donuts,
 * stacked areas, dual axes, gauges, three-dimensional effects"). Callers must
 * already have dropped countries with no value -- display rule 3 (a
 * non-response is a gap, never a zero bar), so this never receives nulls.
 */
export function horizontalBars(
  data: BarDatum[],
  opts: { valueLabel: string; height?: number },
): SVGElement | HTMLElement {
  if (data.length === 0) {
    return emptyChart(opts.height ?? 120);
  }
  const sorted = [...data].sort((a, b) => a.value - b.value);
  return Plot.plot({
    marginLeft: 140,
    height: opts.height ?? Math.max(120, sorted.length * 22),
    x: { label: opts.valueLabel, grid: true, nice: true },
    y: { label: null },
    color: { legend: false },
    marks: [
      Plot.barX(sorted, {
        y: "label",
        x: "value",
        fill: (d: BarDatum) => (d.suppressed ? "var(--color-accent)" : "var(--color-primary)"),
        fillOpacity: (d: BarDatum) => (d.suppressed ? 0.55 : 1),
        tip: true,
        title: (d: BarDatum) => d.title ?? `${d.label}: ${d.value}`,
        channels: { suppressed: "suppressed" },
      }),
      Plot.ruleX([0]),
    ],
  });
}
