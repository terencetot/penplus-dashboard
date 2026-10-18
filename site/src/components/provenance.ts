import { fmtDate } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { GoldRow, ProvenanceStatus, ValueType } from "@/lib/types";

/**
 * Every published figure carries one provenance mark (design brief, 05_design):
 * Historical (ICPPA 2026 country presentations), Validated return, Held (accent
 * outline), No return yet (dashed). Each is a word, never a colour alone
 * (CLAUDE.md rule 9).
 */
export function renderProvenance(status: ProvenanceStatus, detail?: string | null): string {
  const label = t(`prov.${status}`);
  const title = detail ? ` title="${detail.replace(/"/g, "&quot;")}"` : "";
  return `<span class="prov prov--${status}"${title}>${label}</span>`;
}

/** The provenance of one value: held beats its basis. */
export function provenanceOf(v: Pick<GoldRow, "held" | "basis" | "held_by">): string {
  if (v.held === 1) return renderProvenance("held", v.held_by);
  return renderProvenance(v.basis === "form" ? "validated" : "historical");
}

/**
 * "ever enrolled", "active in care", "as of 30 Jun 2026": the value-type label
 * that sits next to a patient figure so a stock, a flow and a dated count are
 * never read as the same thing.
 */
export function valueTypeLabel(
  vt: ValueType | null | undefined,
  asOf?: string | null,
  /** the indicator: workforce figures are "trained", not "enrolled" */
  code?: string,
): string {
  if (!vt) return "";
  if (vt === "point-in-time" && asOf) return t("value_type.as_of", { date: fmtDate(asOf) });
  const prefix = code?.startsWith("3.") ? "value_type.trained_" : "value_type.";
  const key = `${prefix}${vt.split("/")[0]}`;
  const label = t(key);
  return label === key ? vt : label;
}

/** The deck-and-slide reference, e.g. "D3M p224", as a small citation tag. */
export function renderSourceRef(ref: string | null | undefined): string {
  if (!ref) return "";
  return `<span class="source-ref" title="${t("common.source_slide")}">${ref}</span>`;
}
