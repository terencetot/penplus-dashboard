/**
 * Types for the data bundle in /data. These mirror exactly what
 * pipeline/src/penplus_pipeline/export.py writes -- see docs/data-model.md.
 * A field typed `| null` here is a field the pipeline can genuinely emit as
 * `null`, meaning "not reported"; the UI must never coerce it to 0 or "".
 */

export type Cohort = "phase_1" | "phase_2";
export type Verdict = "accepted" | "query" | "hold";
export type SourceKind = "form" | "historical";
export type Unit = "count" | "rate" | "status";
export type Direction = "increase" | "decrease" | "neutral";
export type Confidence = "high" | "medium" | "low" | "not_assessed" | null;
export type Severity = "High" | "Medium" | "Low";

export interface Manifest {
  built_at: string;
  form_version: string;
  model_version: string;
  returns_loaded: number;
  countries: number;
  periods: string; // comma-separated period_id list
  suppress_below: number;
  note: string;
}

export interface CountryRef {
  iso3: string;
  name: string;
  cohort: Cohort;
  returns: number;
  last_period: string | null;
}

export interface HeadlineFigure {
  total: number | null;
  countries_reporting: number;
  countries_total: number;
}

export interface MilestoneStripEntry {
  indicator_code: string;
  label_en: string;
  unit: Unit | null;
  value: number | null;
  as_of: string | null;
  milestone: number | null;
  gap: number | null;
  countries_reporting: number;
  countries_total: number;
}

export interface GoldRow {
  iso3: string;
  period_id: string;
  indicator_code: string;
  disagg_key: string;
  disagg_value: string;
  numerator: number | null;
  denominator: number | null;
  value: number | null;
  unit: Unit;
  completeness: number | null;
  suppressed: 0 | 1;
  as_of: string;
  basis: SourceKind;
}

export interface IndicatorDim {
  indicator_code: string;
  label_en: string;
  family: string | null;
  direction: Direction | null;
  unit: Unit;
  definition: string | null;
  formula: string | null;
  milestone: number | null;
  /** Regional aggregate: sum of numerators (count) or sum(num)/sum(den) (rate),
   *  computed in export.py -- the site never derives this itself. */
  regional_value: number | null;
  regional_as_of: string | null;
  countries_reporting: number;
  gap: number | null;
}

export interface OverviewBundle {
  manifest: Manifest;
  headline: {
    facilities: HeadlineFigure;
    ever_enrolled: HeadlineFigure;
    active: HeadlineFigure;
    trained: HeadlineFigure;
  };
  milestone_strip: MilestoneStripEntry[];
  countries: CountryRef[];
  latest: GoldRow[];
}

export interface IndicatorsBundle {
  manifest: Manifest;
  dim: IndicatorDim[];
  values: GoldRow[];
}

export interface OpenQuery {
  iso3: string;
  period_id: string;
  query_id: number;
  severity: Severity;
  section: string;
  field: string;
  observed: string;
  expected: string;
  question: string;
  status: "open" | "answered" | "closed";
  raised_at: string;
}

export interface QualityRow {
  iso3: string;
  period_id: string;
  source_kind: SourceKind;
  verdict: Verdict;
  ltfu_compliant: 0 | 1 | null;
  dedup_basis: string | null;
  patient_source: string | null;
  facilities_expected: number | null;
  returns_complete: number | null;
  returns_on_time: number | null;
  completeness: number | null;
  conf_facilities: Confidence;
  conf_patients: Confidence;
  conf_workforce: Confidence;
  conf_quality: Confidence;
  conf_governance: Confidence;
  open_queries: number;
}

export interface QualityBundle {
  manifest: Manifest;
  /** Mean completeness over each country's most recent period -- computed in
   *  export.py, not the site (CLAUDE.md rule 1: no arithmetic in the front end). */
  avg_completeness: number | null;
  countries_below_threshold: number;
  rows: QualityRow[];
  open_queries: OpenQuery[];
}

export type FacilityStatus =
  "operational" | "started_this_period" | "under_preparation" | "suspended" | "closed";

export interface FacilityRow {
  facility_id: string;
  iso3: string;
  name: string;
  district: string | null;
  region: string | null;
  facility_type: string | null;
  services_started: string | null;
  conditions: string | null;
  project_supported: "yes" | "no" | "partial" | null;
  status: FacilityStatus | null;
  first_seen: string | null;
  last_seen: string | null;
  period_id_last: string | null;
  active_end: number | null;
  quality_score: number | null;
  readiness_class: "green" | "amber" | "red" | "not_assessed" | null;
}

export interface FacilitiesBundle {
  manifest: Manifest;
  /** Mean quality_score across all facility rows -- computed in export.py,
   *  not the site (CLAUDE.md rule 1: no arithmetic in the front end). */
  avg_quality_score: number | null;
  rows: FacilityRow[];
}

export interface GovernanceRow {
  return_id: number;
  milestone_code: string;
  milestone: string;
  indicator_code: string | null;
  status: "yes" | "no" | "under_development" | "not_applicable" | "not_reported" | null;
  achieved_in: string | null;
  document: string | null;
  /** the period of the most recent return that reported this milestone */
  period_id: string;
}

export type ImplementationStatus = "yes" | "no" | "under_development" | "not_applicable" | null;

/** One of the fourteen steps (Phase_1_PEN-Plus_Reporting_Tools.docx, section
 *  3), either as a reference row (indicators.json-style dimension) or --
 *  when it carries `status` -- one country's standing state on that step. */
export interface ImplementationStepDim {
  step_no: number;
  phase_no: number;
  phase_label: string;
  step_label: string;
}

export interface ImplementationStepRow {
  step_no: number;
  status: ImplementationStatus;
  source: string | null;
  as_of: string | null;
}

export interface CountryImplementation {
  steps: ImplementationStepRow[];
  /** Highest phase (1-5) where every step of it and every phase before it is
   *  'yes'; 0 if even phase 1 is not yet complete. Computed in export.py. */
  highest_phase_completed: number;
}

export interface ImplementationCountry extends CountryImplementation {
  iso3: string;
  name: string;
}

export interface ImplementationBundle {
  manifest: Manifest;
  steps: ImplementationStepDim[];
  countries: ImplementationCountry[];
}

export interface CountryBundle {
  manifest: Manifest;
  country: CountryRef;
  values: GoldRow[];
  facilities: FacilityRow[];
  governance: GovernanceRow[];
  open_queries: OpenQuery[];
  implementation: CountryImplementation;
}

export type StatusVocab = "met" | "partly_met" | "not_met" | "not_reported" | "awaiting_clarification";
