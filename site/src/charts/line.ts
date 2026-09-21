import * as Plot from "@observablehq/plot";
import { emptyChart } from "./empty";

export interface TrendPoint {
  period_id: string;
  value: number | null;
  series: string; // e.g. an ISO3 or "Regional"
  /** shown on hover -- display rule 1: never a rate without n and N. */
  title?: string;
}

/**
 * Lines for trend (CLAUDE.md, Charts). Display rule 3: "NR is not zero. ...
 * a line chart breaks rather than joins across it." Observable Plot's line
 * mark does not connect across a point whose y is null/NaN, so a period with
 * no report must stay IN the data as `value: null` -- never filtered out,
 * which would let the line jump straight across the gap.
 */
export function lineTrend(
  points: TrendPoint[],
  opts: { valueLabel: string; seriesBreakAt?: string; seriesBreakLabel?: string },
): SVGElement | HTMLElement {
  if (points.every((p) => p.value === null)) {
    return emptyChart(320);
  }

  const marks: Plot.Markish[] = [
    Plot.lineY(points, {
      x: "period_id",
      y: (d: TrendPoint) => (d.value === null ? NaN : d.value),
      stroke: "series",
      curve: "linear",
      tip: true,
    }),
    Plot.dot(
      points.filter((d) => d.value !== null),
      {
        x: "period_id",
        y: "value",
        stroke: "series",
        fill: "white",
        r: 3,
        tip: true,
        title: (d: TrendPoint) => d.title ?? `${d.series} ${d.period_id}: ${d.value}`,
      },
    ),
  ];

  if (opts.seriesBreakAt) {
    marks.push(Plot.ruleX([opts.seriesBreakAt], { stroke: "var(--color-accent)", strokeDasharray: "4,3" }));
    if (opts.seriesBreakLabel) {
      const label = opts.seriesBreakLabel;
      marks.push(
        Plot.text([opts.seriesBreakAt], {
          x: (d: string) => d,
          text: () => label,
          frameAnchor: "top",
          dy: 4,
          fill: "var(--color-accent)",
        }),
      );
    }
  }

  return Plot.plot({
    marginLeft: 56,
    height: 320,
    x: { label: null, type: "point" },
    y: { label: opts.valueLabel, grid: true, nice: true, zero: true },
    color: { legend: points.length > 0 && new Set(points.map((p) => p.series)).size > 1 },
    marks,
  });
}
