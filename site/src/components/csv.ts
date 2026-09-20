/**
 * A CSV export on every table (CLAUDE.md, design language, following the NCD
 * Population-based Surveillance Intelligence Platform's pattern). Values are
 * written exactly as displayed -- an NR stays "NR" in the export, it is
 * never written as an empty cell or a 0, so a downstream analyst cannot
 * mistake a non-response for a reported zero.
 */
function csvCell(value: string): string {
  return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}

export function toCSV(headers: string[], rows: string[][]): string {
  const lines = [headers, ...rows].map((row) => row.map(csvCell).join(","));
  return lines.join("\r\n");
}

export function downloadCSV(filename: string, headers: string[], rows: string[][]): void {
  const csv = toCSV(headers, rows);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
