import * as Plot from "@observablehq/plot";
import { emptyChart } from "./empty";
import { fmtCount } from "@/lib/format";

export interface BarDatum {
  label: string;
  /**
   * `null` only for a suppressed cell -- the pipeline withholds the real
   * number below five (CLAUDE.md rule 7), so there is nothing to plot at
   * true scale. A non-response (never reported at all) must not reach this
   * component as a null value; the caller drops those rows entirely
   * (display rule 3: a non-response is a gap, never a bar).
   */
  value: number | null;
  /** true when this bar represents a small, suppressed cell (rendered muted + hatched). */
  suppressed?: boolean;
  /** shown on hover -- display rule 1: never a rate without n and N. */
  title?: string;
  /** an open High query holds this figure: drawn as an outline with the word "Held", out of every total */
  held?: boolean;
}

/**
 * Horizontal bars for comparison across countries (CLAUDE.md, Charts: "Horizontal
 * bars for comparison across countries... Not allowed: pie charts, donuts,
 * stacked areas, dual axes, gauges, three-dimensional effects").
 *
 * Rule 7 is "suppress... and flag the suppression rather than blanking
 * silently": a suppressed country must still appear as a bar -- a short,
 * fixed-width stub, since its real magnitude is not known here -- rather
 * than disappearing from the chart as if it had never reported at all.
 *
 * Renders in exactly the order `data` is given, never re-sorted by value:
 * rule 5 is "no country ranking," and every caller that draws countries
 * already orders them alphabetically before calling this -- sorting by
 * value here would silently turn that back into a ranking (longest bar on
 * top), directly contradicting the "ordered alphabetically, not ranked"
 * caption shown next to every one of these charts. A caller drawing an
 * intrinsically ordered category (e.g. implementation phases 0-5) also
 * depends on this: it is never a ranking, but it does have one correct order.
 */
export function horizontalBars(
  data: BarDatum[],
  opts: { valueLabel: string; height?: number; heldLabel?: string },
): SVGElement | HTMLElement {
  if (data.length === 0) {
    return emptyChart(opts.height ?? 120);
  }
  const known = data.map((d) => d.value).filter((v): v is number => v !== null);
  const stub = known.length > 0 ? Math.max(...known) * 0.04 : 1;
  const plotValue = (d: BarDatum) => d.value ?? stub;
  return Plot.plot({
    width: 1100,
    ariaLabel: opts.valueLabel,
    marginLeft: 230,
    marginRight: 64,
    height: opts.height ?? Math.max(120, data.length * 34 + 40),
    // the panel title already names the indicator; an axis label here only
    // collided with the tick labels
    x: { label: null, grid: true, nice: true, tickFormat: (d: number) => fmtCount(d) },
    y: { label: null, domain: data.map((d) => d.label), padding: 0.45 },
    color: { legend: false },
    style: { fontFamily: "var(--font-family)", fontSize: "13px" },
    marks: [
      Plot.barX(data, {
        y: "label",
        x: plotValue,
        rx: 5,
        fill: (d: BarDatum) =>
          d.held ? "#ffffff" : d.suppressed ? "var(--color-accent)" : "var(--who-blue-deep)",
        fillOpacity: (d: BarDatum) => (d.suppressed ? 0.55 : 1),
        stroke: (d: BarDatum) => (d.held ? "var(--color-accent-strong)" : "none"),
        strokeWidth: 1.5,
        tip: true,
        title: (d: BarDatum) => d.title ?? `${d.label}: ${d.value ?? "suppressed"}`,
        channels: { suppressed: "suppressed" },
      }),
      // colour never carries meaning alone (rule 9): a held bar says so
      Plot.text(
        data.filter((d) => d.held),
        {
          y: "label",
          x: plotValue,
          text: () => opts.heldLabel ?? "Held",
          dx: 8,
          textAnchor: "start",
          fill: "var(--color-accent-strong)",
          fontWeight: 700,
        },
      ),
      // the value at the end of each bar: read, not estimated from the axis
      Plot.text(
        data.filter((d) => !d.held && d.value !== null),
        {
          y: "label",
          x: plotValue,
          text: (d: BarDatum) => fmtCount(d.value),
          dx: 8,
          textAnchor: "start",
          fill: "var(--ink)",
          fontWeight: 700,
        },
      ),
      Plot.ruleX([0]),
    ],
  });
}
