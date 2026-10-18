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
export type Severity = "High" | "Medium" | "Low";
/** How a baseline figure was read from its slide (workbook "Value type"). */
export type ValueType = "flow" | "cumulative" | "active" | "point-in-time" | string;

export interface Manifest {
  built_at: string;
  form_version: string;
  model_version: string;
  returns_loaded: number;
  countries: number;
  periods: string; // comma-separated period_id list
  suppress_below: number;
  public: boolean;
  publish_facility_names: boolean;
  /** true while no validated quarterly form return exists: every screen shows the baseline banner */
  baseline_only: boolean;
  form_returns: number;
  note: string;
}

export interface CountryRef {
  iso3: string;
  name: string;
  cohort: Cohort;
  returns: number;
  last_period: string | null;
  /** at least one non-null published value */
  has_data: boolean;
  /** implementation phase to publish (1-5), null = no return yet */
  phase: number | null;
  form_returns: number;
}

/** A regional figure as export.py builds it: held figures are counted apart and never in `total`. */
export interface RegionalFigure {
  total: number | null;
  /** set when an open regional High query holds the total itself (e.g. Q-REG-01) */
  total_held_by: string | null;
  as_of: string | null;
  countries_reporting: number;
  countries_held: number;
  held_by: string[];
  countries_total: number;
  /** Whole per cent, computed in export.py -- never (re)derived in the browser. */
  coverage_pct: number | null;
  basis: SourceKind | null;
}

export interface MilestoneStripEntry {
  indicator_code: string;
  label_en: string;
  unit: Unit | null;
  value: number | null;
  held_by: string | null;
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
  value_type: ValueType | null;
  /** deck and slide, e.g. "D3M p224" */
  source_ref: string | null;
  held: 0 | 1;
  held_by: string | null;
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
  /** Regional aggregate computed in export.py; null when nothing is reported or the total is held. */
  regional_value: number | null;
  regional_held_by: string | null;
  regional_as_of: string | null;
  countries_reporting: number;
  countries_held: number;
  countries_total: number;
  coverage_pct: number | null;
  gap: number | null;
  value_types: ValueType[];
}

export interface OverviewBundle {
  manifest: Manifest;
  headline: {
    facilities: RegionalFigure;
    sentinel_ever: RegionalFigure;
    all_ever: RegionalFigure;
    sentinel_active: RegionalFigure;
    trained: RegionalFigure;
  };
  milestone_strip: MilestoneStripEntry[];
  countries: CountryRef[];
  countries_with_data: number;
  latest: GoldRow[];
}

export interface IndicatorsBundle {
  manifest: Manifest;
  dim: IndicatorDim[];
  values: GoldRow[];
}

/** One query in the register: seeded from the evidence review, or raised by validate.py. */
export interface Query {
  query_id: string;
  /** an ISO3, "REG", or several ISO3 separated by "; " */
  scope: string;
  severity: Severity;
  indicator: string | null;
  issue: string | null;
  evidence: string | null;
  action: string | null;
  status: "open" | "answered" | "closed";
  resolution: string | null;
  source: string | null;
  rule: string | null;
  period_id: string | null;
  opened_on: string | null;
}

export type ProvenanceStatus = "validated" | "historical" | "held" | "no_return";

export interface ProvenanceRow {
  iso3: string;
  name: string;
  cohort: Cohort;
  evidence_source: "form" | "historical" | "none";
  latest_period: string | null;
  value_types: ValueType[];
  open_queries: number;
  highest_severity: Severity | null;
  status: ProvenanceStatus;
}

export type CoverageCell = "value" | "held" | "not_reported";

export interface CheckSummary {
  rule: string;
  severity: Severity;
  check: string;
  passed: number;
  failed: number;
  not_testable: number;
  failures: { iso3: string; period_id: string; detail: string | null }[];
}

export interface DataSystem {
  iso3: string;
  name: string | null;
  assessed_on: string | null;
  institution: string | null;
  fields: Record<string, string>;
}

export interface QualityBundle {
  manifest: Manifest;
  kpis: {
    validated_returns: { n: number; total: number; period: string | null };
    held_figures: { n: number; regional: number };
    open_queries: { total: number; High: number; Medium: number; Low: number };
    queries_closed: number;
    indicators_covered: { n: number; total: number };
  };
  provenance: ProvenanceRow[];
  coverage: {
    indicators: {
      indicator_code: string;
      label_en: string;
      countries_with_value: number;
      countries_held: number;
      coverage_pct: number | null;
    }[];
    rows: { iso3: string; name: string; cells: Record<string, CoverageCell> }[];
  };
  checks: CheckSummary[];
  held_figures: {
    iso3: string;
    indicator_code: string;
    period_id: string;
    value: number | null;
    held_by: string | null;
  }[];
  held_regional: { indicator_code: string; held_by: string }[];
  queries: Query[];
  data_systems: DataSystem[];
  data_systems_missing: string[];
}

export type RegisterStatus = "active" | "partial" | "planned" | "to_confirm";

export interface FacilityRow {
  facility_id: string;
  iso3: string;
  country: string;
  name: string | null; // withheld (null) only when PUBLISH_FACILITY_NAMES is off
  name_status: "confirmed" | "to_confirm" | null;
  district: string | null;
  region: string | null;
  town: string | null;
  facility_type: string | null;
  services_started: string | null;
  conditions: string | null;
  partner: string | null;
  register_status: RegisterStatus | null;
  source_ref: string | null;
  latitude: number | null;
  longitude: number | null;
  geo_precision: "facility" | "town" | null;
  geo_source: string | null;
  geo_checked: "yes" | "auto" | null;
  /** on the map: coordinates that passed every geocoding rule, or were checked by a person */
  mapped: boolean;
  note: string | null;
  patients_reported: string | null;
}

export interface FacilitiesBundle {
  manifest: Manifest;
  kpis: {
    total: number;
    active: number;
    by_status: Record<string, number>;
    countries: number;
    mapped: number;
    location_to_confirm: number;
    names_to_confirm: number;
  };
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
  /** phase to publish (official ICPPA 2026 map); null = no return yet, never "not started" */
  phase: number | null;
  workbook_phase: number | null;
  icppa_map_phase: number | null;
  /** "no" = the workbook steps and the official map disagree (query Q-PHS-01) */
  agreement: "yes" | "no" | null;
  note: string | null;
  source: string | null;
  has_steps: boolean;
  steps: ImplementationStepRow[];
}

export interface ImplementationCountry extends CountryImplementation {
  iso3: string;
  name: string;
  cohort: Cohort;
}

export interface ImplementationBundle {
  manifest: Manifest;
  steps: ImplementationStepDim[];
  phase_counts: { phase: number; countries: number }[];
  no_return: number;
  with_phase: number;
  disagreements: number;
  countries: ImplementationCountry[];
}

export interface CountryBundle {
  manifest: Manifest;
  country: CountryRef;
  values: GoldRow[];
  facilities: FacilityRow[];
  governance: GovernanceRow[];
  queries: Query[];
  provenance: ProvenanceRow;
  data_system: DataSystem | null;
  implementation: CountryImplementation;
}

export type StatusVocab = "met" | "partly_met" | "not_met" | "not_reported" | "awaiting_clarification";
