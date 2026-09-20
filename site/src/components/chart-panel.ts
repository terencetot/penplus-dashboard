import { t } from "@/lib/i18n";
import { downloadCSV } from "./csv";

export interface ChartPanelOptions {
  title: string;
  caption: string;
  legendHtml?: string;
  buildChart: () => SVGElement | HTMLElement;
  buildTable: () => HTMLElement;
  csv: () => { headers: string[]; rows: string[][] };
  csvFilename: string;
}

/**
 * Every chart on this dashboard is one of these: a title, the caption stating
 * the unit of analysis and how to read it (design language), an accessible
 * table equivalent one click or keypress away (no mouse required), and a CSV
 * export -- the pattern CLAUDE.md asks this build to follow from the NCD
 * Population-based Surveillance Intelligence Platform.
 */
export function renderChartPanel(container: HTMLElement, opts: ChartPanelOptions): void {
  const block = document.createElement("div");
  block.className = "chart-block";

  const header = document.createElement("div");
  header.className = "panel__header";
  const h3 = document.createElement("h3");
  h3.className = "panel__title";
  h3.textContent = opts.title;
  header.appendChild(h3);

  const toolbar = document.createElement("div");
  toolbar.className = "toolbar";

  const toggleBtn = document.createElement("button");
  toggleBtn.type = "button";
  toggleBtn.className = "chart-toggle-table";

  const csvBtn = document.createElement("button");
  csvBtn.type = "button";
  csvBtn.className = "btn";
  csvBtn.textContent = t("common.export_csv");
  csvBtn.addEventListener("click", () => {
    const { headers, rows } = opts.csv();
    downloadCSV(opts.csvFilename, headers, rows);
  });

  toolbar.append(toggleBtn, csvBtn);
  header.appendChild(toolbar);
  block.appendChild(header);

  const body = document.createElement("div");
  body.className = "chart-figure";
  block.appendChild(body);

  const caption = document.createElement("p");
  caption.className = "chart-caption";
  caption.textContent = opts.caption;
  block.appendChild(caption);

  if (opts.legendHtml) {
    const legend = document.createElement("div");
    legend.className = "chart-legend";
    legend.innerHTML = opts.legendHtml;
    block.appendChild(legend);
  }

  let showingTable = false;
  function render() {
    body.replaceChildren(showingTable ? opts.buildTable() : opts.buildChart());
    toggleBtn.textContent = showingTable ? t("common.chart_view") : t("common.table_view");
    toggleBtn.setAttribute("aria-pressed", String(showingTable));
  }
  toggleBtn.addEventListener("click", () => {
    showingTable = !showingTable;
    render();
  });
  render();

  container.appendChild(block);
}
