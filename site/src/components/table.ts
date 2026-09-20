export interface Column<T> {
  key: string;
  label: string;
  numeric?: boolean;
  render: (row: T) => string;
  /** raw value for CSV export; defaults to the rendered string. */
  csv?: (row: T) => string;
  /** set when `render` returns trusted markup (e.g. a status badge), not plain text. */
  html?: boolean;
}

/**
 * An accessible data table: a real <caption>, a real <th scope="col">, and a
 * null cell rendered as a legible "NR" mark rather than emptiness a screen
 * reader would skip over silently. This is also the keyboard- and
 * screen-reader-reachable equivalent every chart must have (specification,
 * section 7).
 */
export function buildTable<T>(caption: string, columns: Column<T>[], rows: T[]): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "data-table-wrap";
  const table = document.createElement("table");
  table.className = "data-table";

  const cap = document.createElement("caption");
  cap.textContent = caption;
  table.appendChild(cap);

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const col of columns) {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = col.label;
    if (col.numeric) th.className = "num";
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const col of columns) {
      const td = document.createElement("td");
      const text = col.render(row);
      if (col.numeric) td.classList.add("num");
      if (col.html) {
        td.innerHTML = text;
      } else {
        if (text === "NR") td.classList.add("cell-null");
        td.append(text === "NR" ? "" : text);
      }
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}

export function tableToCSVData<T>(columns: Column<T>[], rows: T[]): { headers: string[]; rows: string[][] } {
  return {
    headers: columns.map((c) => c.label),
    rows: rows.map((row) => columns.map((c) => (c.csv ?? c.render)(row))),
  };
}
