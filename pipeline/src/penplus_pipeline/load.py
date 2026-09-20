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


def init_db(db_path: str = DB_DEFAULT) -> sqlite3.Connection:
    con = connect(db_path)
    con.executescript(open(os.path.join(HERE, "schema.sql")).read())
    _migrate(con)
    for name, (iso3, cohort) in COUNTRIES.items():
        con.execute("INSERT OR IGNORE INTO dim_country(iso3,name,cohort) VALUES (?,?,?)",
                    (iso3, name, cohort))
    for row in INDICATORS:
        con.execute("INSERT OR REPLACE INTO dim_indicator"
                    "(indicator_code,label_en,family,direction,unit,definition,formula,milestone)"
                    " VALUES (?,?,?,?,?,?,?,?)", row)
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
        con.execute("INSERT OR REPLACE INTO fact_workforce VALUES (?,?,?,?,?,?)",
                    (rid, r["cadre"], r.get("trained_f"), r.get("trained_m"),
                     r.get("fully_trained"), r.get("working_at_site")))
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
                     f.get("active_end"), f.get("months_mentorship"),
                     f.get("quality_score"), f.get("critical_met"), rc))

    q = rec.get("quality") or {}
    exp, comp = q.get("facilities_expected"), q.get("returns_complete")
    completeness = (comp / exp) if (exp and comp is not None and exp > 0) else None
    c = rec.get("confidence") or {}
    con.execute("INSERT OR REPLACE INTO fact_quality VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (rid, exp, comp, q.get("returns_partial"), q.get("returns_none"), completeness,
                 c.get("facilities_and_coverage"), c.get("patients"), c.get("workforce"),
                 c.get("supply_and_service_delivery"), c.get("governance")))
    con.commit()
    return rid


if __name__ == "__main__":
    import sys
    from parse import parse_return
    con = init_db()
    for path in sys.argv[1:]:
        rid = load_return(con, parse_return(path))
        print(f"loaded {os.path.basename(path)} as return {rid}")
