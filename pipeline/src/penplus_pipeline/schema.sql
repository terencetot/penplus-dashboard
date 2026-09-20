-- PEN-Plus regional dashboard: store schema.
-- Grain and nullability follow PEN-Plus_Dashboard_Data_Model.xlsx.
-- NULL always means "not reported". It is never coerced to 0 anywhere.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- dimensions
CREATE TABLE IF NOT EXISTS dim_country (
  iso3            TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  cohort          TEXT NOT NULL CHECK (cohort IN ('phase_1','phase_2')),
  subregion       TEXT
);

CREATE TABLE IF NOT EXISTS dim_period (
  period_id       TEXT PRIMARY KEY,           -- YYYY-Qn or YYYY-MM
  quarter_id      TEXT NOT NULL,              -- YYYY-Qn a monthly period rolls up to
  year            INTEGER NOT NULL,
  rhythm          TEXT NOT NULL CHECK (rhythm IN ('monthly','quarterly','annual')),
  days_in_period  INTEGER,
  closing_date    TEXT
);

CREATE TABLE IF NOT EXISTS dim_facility (
  facility_id       TEXT PRIMARY KEY,         -- ISO3-nnnn, permanent, never reused
  iso3              TEXT NOT NULL REFERENCES dim_country(iso3),
  name              TEXT NOT NULL,
  district          TEXT,
  region            TEXT,
  facility_type     TEXT,
  services_started  TEXT,
  conditions        TEXT,
  project_supported TEXT CHECK (project_supported IN ('yes','no','partial')),
  status            TEXT CHECK (status IN ('operational','started_this_period',
                                           'under_preparation','suspended','closed')),
  first_seen        TEXT,
  last_seen         TEXT
);

CREATE TABLE IF NOT EXISTS dim_indicator (
  indicator_code  TEXT PRIMARY KEY,
  label_en        TEXT NOT NULL,
  family          TEXT,
  direction       TEXT CHECK (direction IN ('increase','decrease','neutral')),
  unit            TEXT CHECK (unit IN ('count','rate','status')),
  definition      TEXT,
  formula         TEXT,
  milestone       REAL                        -- regional target; null until published
);

-- ------------------------------------------------------------------- returns
-- One row per country and period. A return is immutable; a correction is a new
-- revision. Nothing downstream ever reads a superseded revision.
CREATE TABLE IF NOT EXISTS fact_return (
  return_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  iso3            TEXT NOT NULL REFERENCES dim_country(iso3),
  period_id       TEXT NOT NULL REFERENCES dim_period(period_id),
  revision        INTEGER NOT NULL DEFAULT 1,
  superseded      INTEGER NOT NULL DEFAULT 0,
  source_file     TEXT,
  source_kind     TEXT NOT NULL CHECK (source_kind IN ('form','historical')),
  checksum        TEXT,
  received_at     TEXT,
  verdict         TEXT CHECK (verdict IN ('accepted','query','hold')),
  first_return    TEXT,
  ltfu_rule       TEXT,
  ltfu_compliant  INTEGER,
  dedup_basis     TEXT,
  patient_source  TEXT,
  provenance      TEXT,
  UNIQUE (iso3, period_id, revision)
);

-- -------------------------------------------------------------------- facts
CREATE TABLE IF NOT EXISTS fact_patient_stock (          -- stock: never summed
  return_id     INTEGER NOT NULL REFERENCES fact_return(return_id),
  condition     TEXT NOT NULL CHECK (condition IN
                  ('t1d','scd','rhd','severe_htn','other_reported','total')),
  ever_enrolled INTEGER,
  active_end    INTEGER,
  PRIMARY KEY (return_id, condition)
);

CREATE TABLE IF NOT EXISTS fact_patient_flow (           -- flow: summable
  return_id       INTEGER NOT NULL REFERENCES fact_return(return_id),
  condition       TEXT NOT NULL,
  new_enrolled    INTEGER,
  ltfu            INTEGER,
  transferred_out INTEGER,
  stopped         INTEGER,
  died            INTEGER,
  PRIMARY KEY (return_id, condition)
);

CREATE TABLE IF NOT EXISTS fact_patient_age (            -- stock, reconciles to active_end
  return_id  INTEGER NOT NULL REFERENCES fact_return(return_id),
  condition  TEXT NOT NULL,
  age_band   TEXT NOT NULL CHECK (age_band IN ('u15','15_29','30plus','total')),
  patients   INTEGER,
  PRIMARY KEY (return_id, condition, age_band)
);

CREATE TABLE IF NOT EXISTS fact_workforce (
  return_id       INTEGER NOT NULL REFERENCES fact_return(return_id),
  cadre           TEXT NOT NULL,
  trained_f       INTEGER,                                -- flow
  trained_m       INTEGER,                                -- flow
  fully_trained   INTEGER,                                -- stock, cumulative
  working_at_site INTEGER,                                -- stock
  PRIMARY KEY (return_id, cadre)
);

CREATE TABLE IF NOT EXISTS fact_supply (
  return_id        INTEGER NOT NULL REFERENCES fact_return(return_id),
  item             TEXT NOT NULL,
  availability     TEXT CHECK (availability IN
                     ('always','sometimes','never','not_applicable','not_reported')),
  facilities_stockout INTEGER,
  PRIMARY KEY (return_id, item)
);

CREATE TABLE IF NOT EXISTS fact_service (
  return_id INTEGER NOT NULL REFERENCES fact_return(return_id),
  measure   TEXT NOT NULL,
  required  INTEGER NOT NULL DEFAULT 1,
  value     INTEGER,
  PRIMARY KEY (return_id, measure)
);

CREATE TABLE IF NOT EXISTS fact_assumption (
  return_id  INTEGER NOT NULL REFERENCES fact_return(return_id),
  assumption TEXT NOT NULL,
  status     TEXT CHECK (status IN ('holding','under_strain','not_holding','not_assessed')),
  signal     TEXT,
  PRIMARY KEY (return_id, assumption)
);

CREATE TABLE IF NOT EXISTS fact_governance (
  return_id      INTEGER NOT NULL REFERENCES fact_return(return_id),
  milestone_code TEXT NOT NULL,
  milestone      TEXT NOT NULL,
  indicator_code TEXT,
  status         TEXT CHECK (status IN
                   ('yes','no','under_development','not_applicable','not_reported')),
  achieved_in    TEXT,
  document       TEXT,
  PRIMARY KEY (return_id, milestone_code)
);

CREATE TABLE IF NOT EXISTS fact_context (
  return_id INTEGER NOT NULL REFERENCES fact_return(return_id),
  measure   TEXT NOT NULL,
  value     INTEGER,
  PRIMARY KEY (return_id, measure)
);

CREATE TABLE IF NOT EXISTS fact_facility_period (
  return_id        INTEGER NOT NULL REFERENCES fact_return(return_id),
  facility_id      TEXT NOT NULL REFERENCES dim_facility(facility_id),
  return_received  TEXT CHECK (return_received IN ('yes','no','partial')),
  ever_enrolled    INTEGER,
  active_end       INTEGER,
  months_mentorship INTEGER CHECK (months_mentorship BETWEEN 0 AND 3),
  quality_score    INTEGER CHECK (quality_score BETWEEN 0 AND 100),
  critical_met     TEXT CHECK (critical_met IN ('yes','no','partial')),
  readiness_class  TEXT CHECK (readiness_class IN ('green','amber','red','not_assessed')),
  PRIMARY KEY (return_id, facility_id)
);

CREATE TABLE IF NOT EXISTS fact_quality (
  return_id            INTEGER PRIMARY KEY REFERENCES fact_return(return_id),
  facilities_expected  INTEGER,
  returns_complete     INTEGER,
  returns_partial      INTEGER,
  returns_none         INTEGER,
  completeness         REAL,
  conf_facilities      TEXT,
  conf_patients        TEXT,
  conf_workforce       TEXT,
  conf_supply          TEXT,
  conf_governance      TEXT
);

CREATE TABLE IF NOT EXISTS query_register (
  query_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  return_id  INTEGER NOT NULL REFERENCES fact_return(return_id),
  severity   TEXT NOT NULL CHECK (severity IN ('High','Medium','Low')),
  section    TEXT, field TEXT, observed TEXT, expected TEXT, question TEXT,
  status     TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','answered','closed')),
  raised_at  TEXT
);

-- --------------------------------------------------------------------- gold
-- Rebuilt from scratch on every run. Never edited by hand.
CREATE TABLE IF NOT EXISTS gold_indicator (
  iso3           TEXT NOT NULL,
  period_id      TEXT NOT NULL,
  indicator_code TEXT NOT NULL,
  disagg_key     TEXT NOT NULL DEFAULT 'all',
  disagg_value   TEXT NOT NULL DEFAULT 'all',
  numerator      INTEGER,
  denominator    INTEGER,
  value          REAL,
  unit           TEXT,
  completeness   REAL,
  suppressed     INTEGER NOT NULL DEFAULT 0,
  as_of          TEXT,
  basis          TEXT,
  PRIMARY KEY (iso3, period_id, indicator_code, disagg_key, disagg_value)
);

CREATE TABLE IF NOT EXISTS build_manifest (
  built_at        TEXT,
  form_version    TEXT,
  model_version   TEXT,
  returns_loaded  INTEGER,
  countries       INTEGER,
  periods         TEXT
);

CREATE INDEX IF NOT EXISTS ix_gold_country ON gold_indicator(iso3, indicator_code);
CREATE INDEX IF NOT EXISTS ix_return_live  ON fact_return(iso3, period_id, superseded);
