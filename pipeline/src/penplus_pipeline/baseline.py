#!/usr/bin/env python3
"""
baseline.py - load the curated reference files of the ICPPA 2026 baseline.

These are not returns. They are the evidence review's own tables
(docs/refinement/02_data/, copied to data/reference/), loaded as they stand:

  facility_register.csv                    -> dim_facility
  implementation_phase_reconciliation.csv  -> fact_phase, fact_implementation_step
  data_queries.csv                         -> fact_query (status as seeded, see RESOLVED)
  country_data_system_assessment_<ISO3>.csv -> fact_dsa (no respondent names)
"""
from __future__ import annotations

import csv
import datetime as dt
import glob
import os
import re

from common import COUNTRIES

HERE = os.path.dirname(os.path.abspath(__file__))
REFERENCE = os.path.join(HERE, "..", "..", "..", "data", "reference")

PROV_REGISTER = "facility_register.csv (ICPPA 2026 decks, evidence review of 17 Oct 2026)"
PROV_PHASES = ("implementation_phase_reconciliation.csv: PEN_PLUS_MONITORING.xlsx steps"
               " and the official WHO AFRO phase map shown at ICPPA 2026 (D2M p7)")

#: Register status -> dim_facility.status. Only 'active' is a facility
#: providing PEN-Plus services (indicator 2.3). 'partial' (Uganda's Luwero:
#: principles in training, full model not operational) and 'to_confirm'
#: (Liberia's orientation sites, Q-LBR-03) are shown, never counted.
REGISTER_STATUS = {"active": "operational", "planned": "under_preparation",
                   "partial": None, "to_confirm": None}

#: Seeded queries whose action is a pipeline or dashboard change this
#: refinement makes. They are closed with what was done; the rest stay as
#: seeded. Recorded in docs/refinement/RUN_LOG.md.
RESOLVED = {
    "Q-REG-02": "Severe hypertension removed from every sentinel total (common.TRACERS);"
                " it stays visible as its own condition.",
    "Q-REG-03": "A country now counts as reporting only with a non-null value; coverage is"
                " shown per indicator.",
    "Q-BFA-02": "Republished: Burkina Faso sentinel = SCD 500. The 3,402 HTA sit under severe"
                " hypertension, outside the sentinel total.",
    "Q-COD-01": "Republished: DRC sentinel = SCD 7 (HTA 563 outside the sentinel total). The T1D"
                " split still has to be requested from the WCO.",
    "Q-UGA-01": "Republished 2,226 for the sentinel conditions; severe HTN 15 shown separately.",
    "Q-KEN-01": "Loaded from the corrected extraction: 4 sites, 559 cumulative (T1D 310).",
    "Q-NGA-01": "Wuse General Hospital loaded from the facility register.",
    "Q-SLE-01": "Facility register status used: 2 active, 2 planned.",
    "Q-COG-01": "Facility register status used: 1 active unit, 3 pilot districts planned.",
    # Programme decision, 18 Oct 2026 (docs/review/REVUE_DASHBOARD.md): the
    # regional figure is published as the sum of the country-reported figures,
    # always shown with its country coverage.
    "Q-REG-01": "Decision of the programme (18 Oct 2026): the regional figure is the sum of the"
                " figures each country reported, shown with the number of countries it covers."
                " Zimbabwe stays out of the sum while Q-ZWE-01 is open.",
}


def _read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _iso3(name):
    entry = COUNTRIES.get((name or "").strip())
    return entry[0] if entry else None


def _float(v):
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def load_facility_register(con, path=None) -> int:
    """Replace dim_facility with the curated register. Facilities are no
    longer derived from free-text site names (audit v2, section 1)."""
    path = path or os.path.join(REFERENCE, "facility_register.csv")
    rows = _read(path)
    con.execute("DELETE FROM dim_facility WHERE facility_id NOT IN"
                " (SELECT facility_id FROM fact_facility_period)")
    for r in rows:
        from_seed = r["service_start"] or None
        ref = None
        if r.get("source_deck"):
            from seed_history import source_ref
            ref = source_ref(r["source_deck"], r.get("source_page"))
        con.execute(
            "INSERT OR REPLACE INTO dim_facility(facility_id,iso3,name,district,region,"
            "facility_type,services_started,conditions,project_supported,status,first_seen,"
            "last_seen,name_status,town,partner,register_status,source_ref,latitude,longitude,"
            "geo_precision,geo_source,geo_checked,note,patients_reported)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["facility_id"], r["iso3"], r["facility_name"], r["admin2_district"] or None,
             r["admin1_region"] or None, r["facility_level"] or None, from_seed,
             r["conditions"] or None, None, REGISTER_STATUS.get(r["status"]),
             "2026-A", "2026-A", r["name_status"] or None, r["town"] or None,
             r["implementing_partner"] or None, r["status"], ref,
             _float(r.get("latitude")), _float(r.get("longitude")),
             r.get("geo_precision") or None, r.get("geo_source") or None,
             r.get("geo_checked") or None, r.get("note") or None,
             r.get("patients_reported") or None))
    _apply_curated_coordinates(con)
    con.commit()
    return len(rows)


def _apply_curated_coordinates(con, path=None) -> int:
    """Coordinates found for facilities the automatic OpenStreetMap rules
    could not place (data/reference/facility_coordinates.csv): the WHO/KEMRI
    list of public health facilities in sub-Saharan Africa (national master
    facility lists, mostly GPS) where the facility is in it, otherwise the
    town, marked approximate. A point already checked by the protocol
    (geo_checked auto or yes) is never overwritten."""
    path = path or os.path.join(REFERENCE, "facility_coordinates.csv")
    if not os.path.exists(path):
        return 0
    n = 0
    for r in _read(path):
        cur = con.execute("UPDATE dim_facility SET latitude=?, longitude=?, geo_precision=?,"
                          " geo_checked=?, geo_source=?, note=COALESCE(note || ' ', '') || ?"
                          " WHERE facility_id=? AND COALESCE(geo_checked,'') NOT IN ('auto','yes')",
                          (_float(r["latitude"]), _float(r["longitude"]), r["geo_precision"],
                           r["geo_checked"], r["geo_source"], f"[Location: {r['note']}]",
                           r["facility_id"]))
        n += cur.rowcount
    return n


def load_phase_reconciliation(con, path=None) -> int:
    """The phase to publish per country, and the workbook's 14 steps.

    The official WHO AFRO map at ICPPA (June 2026) is the more recent source;
    where the monitoring workbook disagrees (Ghana, Kenya, Mozambique, Niger,
    Nigeria: Q-PHS-01) the map's phase is published and the disagreement is
    shown. A second-round country with no return gets no phase at all, never
    "not started".
    """
    path = path or os.path.join(REFERENCE, "implementation_phase_reconciliation.csv")
    today = dt.date.today().isoformat()
    n = 0
    for r in _read(path):
        iso3 = _iso3(r["country"])
        if not iso3:
            continue

        def _p(v):
            return int(v) if (v or "").strip().isdigit() else None

        con.execute(
            "INSERT OR REPLACE INTO fact_phase(iso3,workbook_phase,icppa_map_phase,"
            "phase_to_publish,agreement,note,source) VALUES (?,?,?,?,?,?,?)",
            (iso3, _p(r["workbook_phase"]), _p(r["icppa_map_phase"]),
             _p(r["phase_to_publish"]),
             {"yes": "yes", "no": "no"}.get((r["agreement"] or "").strip().lower()),
             r["note"] or None, PROV_PHASES))
        for step in range(1, 15):
            v = (r.get(f"step_{step}") or "").strip().upper()
            status = {"Y": "yes", "N": "no"}.get(v)
            if status:
                con.execute(
                    "INSERT OR REPLACE INTO fact_implementation_step(iso3,step_no,status,source,as_of)"
                    " VALUES (?,?,?,?,?)",
                    (iso3, step, status, "PEN_PLUS_MONITORING.xlsx, PEN plus phases sheet", today))
        n += 1
    con.commit()
    return n


def load_queries(con, path=None) -> tuple[int, int]:
    """Seed fact_query from the evidence review. Returns (seeded, closed)."""
    path = path or os.path.join(REFERENCE, "data_queries.csv")
    con.execute("DELETE FROM fact_query WHERE source='evidence review'")
    rows = _read(path)
    closed = 0
    for r in rows:
        resolution = RESOLVED.get(r["query_id"])
        status = "closed" if resolution else (r["status"] or "open").strip().lower()
        closed += 1 if resolution else 0
        con.execute(
            "INSERT OR REPLACE INTO fact_query(query_id,scope,severity,indicator,issue,evidence,"
            "action,status,resolution,source,rule,period_id,opened_on)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["query_id"], r["iso3"], r["severity"], r["indicator"], r["issue"],
             r["evidence"], r["action"], status, resolution, "evidence review", None, None,
             "2026-10-17"))
    con.commit()
    return len(rows), closed


#: Assessment answers kept for the readiness panel. Respondent names and
#: e-mail addresses are never read, even if a later file carries them.
DSA_FIELDS = {
    1: "how_recorded", 2: "standard_register", 3: "patient_id", 4: "hmis_platform",
    6: "where_entered", 7: "emr_district", 10: "can_carry_quarterly",
    12: "can_add_indicators", 13: "main_constraint",
}


def load_data_system_assessments(con, pattern=None) -> int:
    pattern = pattern or os.path.join(REFERENCE, "country_data_system_assessment_*.csv")
    con.execute("DELETE FROM fact_dsa")
    n = 0
    for path in sorted(glob.glob(pattern)):
        for r in _read(path):
            q = int(r["q_no"]) if (r.get("q_no") or "").isdigit() else None
            if q not in DSA_FIELDS:
                continue
            response = r["response"]
            if q == 4:
                response = re.sub(r"^platform:\s*", "", response, flags=re.I)
            con.execute("INSERT OR REPLACE INTO fact_dsa(iso3,assessed_on,institution,field,"
                        "question,response) VALUES (?,?,?,?,?,?)",
                        (r["iso3"], r["date"], r.get("respondent_institution"),
                         DSA_FIELDS[q], r["question"], response))
        n += 1
    con.commit()
    return n
