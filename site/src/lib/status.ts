import type { StatusVocab } from "./types";

/**
 * Display rule 8 (CLAUDE.md, non-negotiable rule 9 / specification rule 8):
 * "Colour never carries meaning alone." Status is always accompanied by a
 * label or a mark, and the vocabulary is exactly: met, partly met, not met,
 * not reported. `awaiting_clarification` is the fifth, dashboard-only state
 * for a country on hold (non-negotiable rule 10) -- it is never collapsed
 * into "not reported", which would misrepresent a pending query as silence.
 */
const FALLBACK_LABELS: Record<StatusVocab, string> = {
  met: "Met",
  partly_met: "Partly met",
  not_met: "Not met",
  not_reported: "Not reported",
  awaiting_clarification: "Awaiting clarification",
};

/** The i18n key for a status; screens should render via `t(statusKey(status))`. */
export function statusKey(status: StatusVocab): string {
  return `status.${status}`;
}

export function statusLabel(status: StatusVocab): string {
  return FALLBACK_LABELS[status];
}

/** governance milestone status (yes/no/under_development/...) -> the four-state vocabulary. */
export function statusFromGovernance(
  status: string | null | undefined,
  documentTitled: boolean,
): StatusVocab {
  // Data model rule: "A Yes without a document title is not counted."
  if (status === "yes" && documentTitled) return "met";
  if (status === "yes" && !documentTitled) return "not_met";
  if (status === "under_development") return "partly_met";
  if (status === "no") return "not_met";
  return "not_reported";
}

/**
 * A facility readiness rating (green/amber/red/not_assessed) already IS a
 * traffic-light readiness judgment, unlike a facility's 5-state operational
 * status (operational/suspended/closed/...), which does not map onto
 * met/partly-met/not-met without distorting its meaning (a closed facility
 * is not necessarily a "failure" the way "not met" implies) -- see the
 * comment on verdictKey in vocab.ts for the prior instance of exactly this
 * mistake. Readiness is different: green genuinely means the criteria were
 * met, amber partly, red not, and not_assessed is exactly "not reported."
 */
export function statusFromReadiness(
  value: "green" | "amber" | "red" | "not_assessed" | null | undefined,
): StatusVocab {
  if (value === "green") return "met";
  if (value === "amber") return "partly_met";
  if (value === "red") return "not_met";
  return "not_reported";
}

/** implementation-step status (yes/no/under_development/...) -> the four-state vocabulary. */
export function statusFromImplementationStep(
  status: "yes" | "no" | "under_development" | "not_applicable" | null | undefined,
): StatusVocab {
  if (status === "yes") return "met";
  if (status === "under_development") return "partly_met";
  if (status === "no") return "not_met";
  return "not_reported";
}

export function renderStatus(status: StatusVocab, label: string): string {
  return `<span class="status status--${status}">${label}</span>`;
}
