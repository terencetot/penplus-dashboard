/**
 * i18n key builders for the form's small controlled vocabularies (facility
 * status, project-supported, readiness class). Mirrors `statusKey` in
 * status.ts: screens call `t(facilityStatusKey(value))` rather than
 * rendering the raw enum token, so a French or Portuguese viewer never sees
 * an English code like "operational" sitting in an otherwise translated row.
 */
import type { FacilityRow, Severity, Verdict } from "./types";

export function severityKey(severity: Severity): string {
  return `severity.${severity.toLowerCase()}`;
}

/**
 * A return's processing verdict (accepted/query/hold) is not a milestone
 * judgment, so it does not belong in status.ts's met/partly-met/not-met
 * vocabulary -- reusing that for "accepted" or "query" previously rendered
 * an accepted return as "Not reported", which is exactly the kind of
 * misleading label the vocabulary rule exists to prevent. Only `hold` keeps
 * the shared "awaiting clarification" treatment non-negotiable rule 10
 * specifically asks for; render that case with `renderStatus`, and
 * "accepted"/"query" as a plain chip with this key.
 */
export function verdictKey(verdict: Verdict): string {
  return `verdict.${verdict}`;
}

export function facilityStatusKey(status: FacilityRow["status"]): string {
  return status ? `facility_status.${status}` : "";
}

export function projectSupportedKey(value: FacilityRow["project_supported"]): string {
  return value ? `project_supported.${value}` : "";
}

export function readinessKey(value: FacilityRow["readiness_class"]): string {
  return value ? `readiness.${value}` : "";
}
