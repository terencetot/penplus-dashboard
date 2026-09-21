/**
 * i18n key builders for the form's small controlled vocabularies (facility
 * status, project-supported, readiness class). Mirrors `statusKey` in
 * status.ts: screens call `t(facilityStatusKey(value))` rather than
 * rendering the raw enum token, so a French or Portuguese viewer never sees
 * an English code like "operational" sitting in an otherwise translated row.
 */
import type { FacilityRow, Severity } from "./types";

export function severityKey(severity: Severity): string {
  return `severity.${severity.toLowerCase()}`;
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
