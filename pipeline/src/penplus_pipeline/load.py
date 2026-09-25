#!/usr/bin/env python3
"""
load.py - write a parsed return into the SQLite store.

Returns are immutable. Re-loading the same country and period creates a new
revision and marks the previous one superseded; nothing is ever overwritten, so a
figure published last quarter can always be reproduced.
"""
from __future__ import annotations

import datetime as dt
import os
import sqlite3

from common import COUNTRIES, INDICATORS, resolve_iso3

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DEFAULT = os.path.join(HERE, "penplus.db")


def connect(db_path: str = DB_DEFAULT) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _migrate(con: sqlite3.Connection) -> None:
    """Add columns introduced after a store was first created.

    `CREATE TABLE IF NOT EXISTS` in schema.sql leaves an existing table alone,
    so a column added to the schema later needs an explicit, idempotent
    migration here rather than a rebuild that would discard loaded returns.
    """
    cols = {r["name"] for r in con.execute("PRAGMA table_info(dim_indicator)")}
    if "milestone" not in cols:
        con.execute("ALTER TABLE dim_indicator ADD COLUMN milestone REAL")
    if "reporting_frequency" not in cols:
        con.execute("ALTER TABLE dim_indicator ADD COLUMN reporting_frequency TEXT")

    # Corrected against the real v3 form (docs/architecture.md): the facility
    # mentorship field is a quarterly yes/no, not a 0-3 month count, and the
    # fifth confidence domain is "quality and mentorship", not "supply".
    fp_cols = {r["name"] for r in con.execute("PRAGMA table_info(fact_facility_period)")}
    if "mentorship_visit" not in fp_cols and "months_mentorship" in fp_cols:
        con.execute("ALTER TABLE fact_facility_period RENAME COLUMN months_mentorship TO mentorship_visit")

    q_cols = {r["name"] for r in con.execute("PRAGMA table_info(fact_quality)")}
    if "conf_quality" not in q_cols and "conf_supply" in q_cols:
        con.execute("ALTER TABLE fact_quality RENAME COLUMN conf_supply TO conf_quality")
    if "returns_on_time" not in q_cols:
        con.execute("ALTER TABLE fact_quality ADD COLUMN returns_on_time INTEGER")
    # Current form revision: completeness/timeliness partly self-reported
    # under 5.1, plus a new reconciliation self-attestation block.
    for col in ("reported_completeness_pct REAL", "reported_timeliness_pct REAL",
                "recon_annex_a_vs_2_3 TEXT", "recon_patients_vs_2_5_2_6 TEXT",
                "recon_mentorship_vs_3_4 TEXT", "recon_definition_changed TEXT",
                "recon_figure_corrected TEXT"):
        name = col.split()[0]
        if name not in q_cols:
            con.execute(f"ALTER TABLE fact_quality ADD COLUMN {col}")

    wf_cols = {r["name"] for r in con.execute("PRAGMA table_info(fact_workforce)")}
    if "trained_ns" not in wf_cols:
        con.execute("ALTER TABLE fact_workforce ADD COLUMN trained_ns INTEGER")


def init_db(db_path: str = DB_DEFAULT) -> sqlite3.Connection:
    con = connect(db_path)
    con.executescript(open(os.path.join(HERE, "schema.sql")).read())
    _migrate(con)
    for name, (iso3, cohort) in COUNTRIES.items():
        con.execute("INSERT OR IGNORE INTO dim_country(iso3,name,cohort) VALUES (?,?,?)",
                    (iso3, name, cohort))
    for row in INDICATORS:
        con.execute("INSERT OR REPLACE INTO dim_indicator"
                    "(indicator_code,label_en,family,direction,unit,definition,formula,milestone,"
                    "reporting_frequency)"
                    " VALUES (?,?,?,?,?,?,?,?,?)", row)
    con.commit()
    return con


def _ensure_period(con, rec):
    con.execute(
        "INSERT OR IGNORE INTO dim_period(period_id,quarter_id,year,rhythm,days_in_period,closing_date)"
        " VALUES (?,?,?,?,?,?)",
        (rec["period_id"], rec.get("quarter_id"), rec.get("year"),
         rec.get("rhythm", "quarterly"), rec.get("days_in_period"), rec.get("closing_date")))


def load_return(con, rec, source_kind="form", provenance=None, verdict="accepted") -> int:
    """Insert one return and everything hanging off it. Returns the return_id."""
    iso3 = resolve_iso3(rec.get("country_name"))
    _ensure_period(con, rec)

    prev = con.execute(
        "SELECT MAX(revision) r FROM fact_return WHERE iso3=? AND period_id=?",
        (iso3, rec["period_id"])).fetchone()["r"]
    revision = (prev or 0) + 1
    con.execute("UPDATE fact_return SET superseded=1 WHERE iso3=? AND period_id=?",
                (iso3, rec["period_id"]))

    cur = con.execute(
        "INSERT INTO fact_return(iso3,period_id,revision,superseded,source_file,source_kind,"
        "checksum,received_at,verdict,first_return,ltfu_rule,ltfu_compliant,dedup_basis,"
        "patient_source,provenance) VALUES (?,?,?,0,?,?,?,?,?,?,?,?,?,?,?)",
        (iso3, rec["period_id"], revision, rec.get("source_file"), source_kind,
         rec.get("checksum"), dt.date.today().isoformat(), verdict,
         rec.get("first_return"), rec.get("ltfu_rule"), rec.get("ltfu_compliant"),
         rec.get("dedup_basis"), rec.get("patient_source"), provenance))
    rid = cur.lastrowid

    for r in rec.get("patient_stock", []):
        con.execute("INSERT OR REPLACE INTO fact_patient_stock VALUES (?,?,?,?)",
                    (rid, r["condition"], r.get("ever_enrolled"), r.get("active_end")))
    for r in rec.get("patient_flow", []):
        con.execute("INSERT OR REPLACE INTO fact_patient_flow VALUES (?,?,?,?,?,?,?)",
                    (rid, r["condition"], r.get("new_enrolled"), r.get("ltfu"),
                     r.get("transferred_out"), r.get("stopped"), r.get("died")))
    for r in rec.get("patient_age", []):
        con.execute("INSERT OR REPLACE INTO fact_patient_age VALUES (?,?,?,?)",
                    (rid, r["condition"], r["age_band"], r.get("patients")))
    for r in rec.get("workforce", []):
        con.execute("INSERT OR REPLACE INTO fact_workforce VALUES (?,?,?,?,?,?,?)",
                    (rid, r["cadre"], r.get("trained_f"), r.get("trained_m"), r.get("trained_ns"),
                     r.get("fully_trained"), r.get("working_at_site")))
    for r in rec.get("workforce_tot", []):
        con.execute("INSERT OR REPLACE INTO fact_workforce_tot VALUES (?,?,?,?,?)",
                    (rid, r["cadre"], r.get("trained_f"), r.get("trained_m"), r.get("trained_ns")))
    for r in rec.get("supply", []):
        con.execute("INSERT OR REPLACE INTO fact_supply VALUES (?,?,?,?)",
                    (rid, r["item"], r.get("availability"), r.get("facilities_stockout")))
    for r in rec.get("service", []):
        con.execute("INSERT OR REPLACE INTO fact_service VALUES (?,?,?,?)",
                    (rid, r["measure"], r.get("required", 1), r.get("value")))
    for r in rec.get("assumptions", []):
        con.execute("INSERT OR REPLACE INTO fact_assumption VALUES (?,?,?,?)",
                    (rid, r["assumption"], r.get("status"), r.get("signal")))
    for r in rec.get("governance", []):
        con.execute("INSERT OR REPLACE INTO fact_governance VALUES (?,?,?,?,?,?,?)",
                    (rid, r["milestone_code"], r["milestone"], r.get("indicator_code"),
                     r.get("status"), r.get("achieved_in"), r.get("document")))
    for k, v in (rec.get("context") or {}).items():
        con.execute("INSERT OR REPLACE INTO fact_context VALUES (?,?,?)", (rid, k, v))
    for k, v in (rec.get("training_capacity") or {}).items():
        con.execute("INSERT OR REPLACE INTO fact_context VALUES (?,?,?)", (rid, k, v))
    for r in rec.get("retention", []):
        con.execute("INSERT OR REPLACE INTO fact_context VALUES (?,?,?)",
                    (rid, f"retention_num_{r['condition']}", r.get("numerator")))
        con.execute("INSERT OR REPLACE INTO fact_context VALUES (?,?,?)",
                    (rid, f"retention_den_{r['condition']}", r.get("denominator")))

    # facilities: identity is slowly changing, performance is per period
    for f in rec.get("facilities", []):
        fid = f.get("facility_id")
        if not fid:
            continue
        con.execute(
            "INSERT INTO dim_facility(facility_id,iso3,name,district,region,facility_type,"
            "services_started,conditions,project_supported,status,first_seen,last_seen)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(facility_id) DO UPDATE SET name=excluded.name,district=excluded.district,"
            "region=excluded.region,facility_type=excluded.facility_type,"
            "conditions=excluded.conditions,project_supported=excluded.project_supported,"
            "status=excluded.status,last_seen=excluded.last_seen",
            (fid, iso3, f.get("name"), f.get("district"), f.get("region"),
             f.get("facility_type"), f.get("services_started"), f.get("conditions"),
             f.get("project_supported"), f.get("status"),
             rec["period_id"], rec["period_id"]))
    for f in rec.get("facility_period", []):
        fid = f.get("facility_id")
        if not fid:
            continue
        con.execute("INSERT OR IGNORE INTO dim_facility(facility_id,iso3,name,first_seen,last_seen)"
                    " VALUES (?,?,?,?,?)",
                    (fid, iso3, f.get("name"), rec["period_id"], rec["period_id"]))
        rc = f.get("readiness_class")
        rc = rc if rc in ("green", "amber", "red", "not_assessed") else None
        con.execute("INSERT OR REPLACE INTO fact_facility_period VALUES (?,?,?,?,?,?,?,?,?)",
                    (rid, fid, f.get("return_received"), f.get("ever_enrolled"),
                     f.get("active_end"), f.get("mentorship_visit"),
                     f.get("quality_score"), f.get("critical_met"), rc))

    q = rec.get("quality") or {}
    exp, comp = q.get("facilities_expected"), q.get("returns_complete")
    completeness = (comp / exp) if (exp and comp is not None and exp > 0) else None
    c = rec.get("confidence") or {}
    rc = rec.get("reconciliation") or {}
    con.execute("INSERT OR REPLACE INTO fact_quality VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (rid, exp, comp, q.get("returns_partial"), q.get("returns_none"),
                 q.get("returns_on_time"), completeness,
                 q.get("reported_completeness_pct"), q.get("reported_timeliness_pct"),
                 c.get("facilities_and_coverage"), c.get("patients"), c.get("workforce"),
                 c.get("quality_mentorship"), c.get("governance_financing_hmis"),
                 rc.get("annex_a_vs_2_3"), rc.get("patients_vs_2_5_2_6"),
                 rc.get("mentorship_vs_3_4"), rc.get("definition_changed"),
                 rc.get("figure_corrected")))
    con.commit()
    return rid


def load_implementation_steps(con, iso3: str, steps: dict[int, str], source: str, as_of: str) -> None:
    """Record one country's implementation-phase status.

    `steps` maps step_no -> status ('yes'/'no'/'under_development'/
    'not_applicable'/'not_reported'); a step not present in the dict is left
    untouched rather than overwritten with 'not_reported', so a later,
    partial update (e.g. one phase re-assessed) never erases an earlier
    country's other steps.
    """
    for step_no, status in steps.items():
        con.execute(
            "INSERT INTO fact_implementation_step(iso3,step_no,status,source,as_of)"
            " VALUES (?,?,?,?,?)"
            " ON CONFLICT(iso3,step_no) DO UPDATE SET"
            " status=excluded.status, source=excluded.source, as_of=excluded.as_of",
            (iso3, step_no, status, source, as_of))
    con.commit()


if __name__ == "__main__":
    import sys

    from parse import parse_return
    con = init_db()
    for path in sys.argv[1:]:
        rid = load_return(con, parse_return(path))
        print(f"loaded {os.path.basename(path)} as return {rid}")
