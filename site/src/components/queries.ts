import { t } from "@/lib/i18n";
import { severityKey } from "@/lib/vocab";
import type { Query } from "@/lib/types";

const SEVERITY_ORDER: Record<string, number> = { High: 0, Medium: 1, Low: 2 };

/** Open queries first, then by severity, then by id. Ordering only. */
export function sortQueries(queries: Query[]): Query[] {
  return [...queries].sort(
    (a, b) =>
      Number(a.status !== "open") - Number(b.status !== "open") ||
      (SEVERITY_ORDER[a.severity] ?? 3) - (SEVERITY_ORDER[b.severity] ?? 3) ||
      a.query_id.localeCompare(b.query_id),
  );
}

/** A query as a card: id, severity in words, indicator, issue, evidence, action, status. */
export function renderQueryCard(q: Query): string {
  const closed = q.status !== "open";
  return `<div class="query-card query-card--${q.severity.toLowerCase()}${closed ? " is-closed" : ""}">
    <div class="query-card__head">
      <b class="query-card__id">${q.query_id}</b>
      <span class="sev sev--${q.severity.toLowerCase()}">${t(severityKey(q.severity))}</span>
      ${q.indicator ? `<span class="chip">${q.indicator}</span>` : ""}
      <span class="query-card__status">${t(`query_status.${q.status}`)}</span>
    </div>
    <p class="query-card__issue">${q.issue ?? ""}</p>
    ${q.evidence ? `<p class="query-card__meta"><span>${t("table.evidence")}:</span> ${q.evidence}</p>` : ""}
    ${q.action ? `<p class="query-card__meta"><span>${t("table.action")}:</span> ${q.action}</p>` : ""}
    ${q.resolution ? `<p class="query-card__meta query-card__resolution"><span>${t("table.resolution")}:</span> ${q.resolution}</p>` : ""}
  </div>`;
}

export function renderQueryList(queries: Query[]): string {
  return `<div class="query-list">${sortQueries(queries).map(renderQueryCard).join("")}</div>`;
}
