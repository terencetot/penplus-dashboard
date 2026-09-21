#!/usr/bin/env python3
"""
transform.py - build gold_indicator from the live returns.

One implementation per indicator, in one place. The dashboard never computes;
it reads what this writes. Rebuilt from scratch on every run, so a figure can
always be reproduced from the raw returns.

NULL discipline: a numerator or denominator that is None produces a value of
None. Nothing is coerced to zero, and a None never enters a sum as zero.
"""
from __future__ import annotations

import datetime as dt

from common import TRACERS
from load import DB_DEFAULT, connect

SUPPRESS_BELOW = 5


def _sum(values):
    """Sum that stays honest: returns None if every input is None."""
    vals = [v for v in values if v is not None]
    return sum(vals) if vals else None


def _rate(num, den):
    if num is None or den in (None, 0):
        return None
    return round(num / den, 4)


def live_returns(con):
    return list(con.execute(
        "SELECT r.*, p.quarter_id, p.closing_date, q.completeness"
        " FROM fact_return r JOIN dim_period p USING(period_id)"
        " LEFT JOIN fact_quality q USING(return_id)"
        " WHERE r.superseded=0 AND r.verdict IN ('accepted','query')"
        " ORDER BY r.iso3, r.period_id"))


def build(db_path: str = DB_DEFAULT):
    con = connect(db_path)
    con.execute("DELETE FROM gold_indicator")
    rows = []

    for r in live_returns(con):
        rid, iso3, pid = r["return_id"], r["iso3"], r["period_id"]
        comp, as_of = r["completeness"], r["closing_date"]
        basis = r["source_kind"]

        def put(code, num=None, den=None, unit="count", key="all", val="all", value=None):
            v = value if value is not None else (num if unit == "count" else _rate(num, den))
            rows.append((iso3, pid, code, key, val, num, den, v, unit, comp,
                         1 if (num is not None and num < SUPPRESS_BELOW and unit == "count"
                               and key != "all") else 0,
                         as_of, basis))

        # ---- 2.5 and 2.6: patients, tracers only
        stock = {s["condition"]: s for s in con.execute(
            "SELECT * FROM fact_patient_stock WHERE return_id=?", (rid,))}
        ever = _sum(stock[c]["ever_enrolled"] for c in TRACERS if c in stock)
        active = _sum(stock[c]["active_end"] for c in TRACERS if c in stock)
        put("2.5", num=ever)
        put("2.6", num=active)
        for c in TRACERS:
            if c in stock:
                put("2.5", num=stock[c]["ever_enrolled"], key="condition", val=c)
                put("2.6", num=stock[c]["active_end"], key="condition", val=c)
        if "other_reported" in stock:
            put("2.5", num=stock["other_reported"]["ever_enrolled"],
                key="condition", val="other_reported")

        for a in con.execute(
                "SELECT age_band, SUM(patients) n FROM fact_patient_age"
                " WHERE return_id=? AND condition!='total' GROUP BY age_band", (rid,)):
            if a["age_band"] != "total":
                put("2.6", num=a["n"], key="age_band", val=a["age_band"])

        # fact_context holds everything sourced from a single Item/Response
        # cell rather than a per-condition or per-cadre table: read it once.
        ctx = {c["measure"]: c["value"] for c in con.execute(
            "SELECT measure,value FROM fact_context WHERE return_id=?", (rid,))}

        # ---- 2.6b: retention, only where the regional rule was applied
        if r["ltfu_compliant"] == 1:
            for c in TRACERS + ["total"]:
                n, d = ctx.get(f"retention_num_{c}"), ctx.get(f"retention_den_{c}")
                if n is not None or d is not None:
                    put("2.6b", num=n, den=d, unit="rate",
                        key="condition" if c != "total" else "all",
                        val=c if c != "total" else "all")

        # ---- 2.1: guideline dissemination, tracers only
        disseminated = [ctx.get(f"guideline_disseminated_{c}") for c in TRACERS]
        reported = [v for v in disseminated if v is not None]
        if reported:
            put("2.1", num=sum(1 for v in reported if v == 1), den=len(TRACERS), unit="rate")

        # ---- 1.1, 1.2, 1.3: governance milestones, per the fixed Results
        # Framework codes. A Yes without a document title is not counted.
        for g in con.execute(
                "SELECT milestone_code, status, document FROM fact_governance"
                " WHERE return_id=? AND milestone_code IN ('1.1','1.2','1.3')", (rid,)):
            achieved = 1 if (g["status"] == "yes" and g["document"]) else \
                (0 if g["status"] in ("yes", "no", "under_development") else None)
            put(g["milestone_code"], num=achieved)

        # ---- 4.1: resource-mobilization round table
        if ctx.get("round_table_held") is not None:
            put("4.1", num=ctx["round_table_held"])

        # ---- 2.3, 2.4, 3.4: derived from the facility annex
        fac = list(con.execute(
            "SELECT fp.*, f.status FROM fact_facility_period fp"
            " JOIN dim_facility f USING(facility_id) WHERE fp.return_id=?", (rid,)))
        if not fac:
            fac = list(con.execute(
                "SELECT NULL return_received, NULL mentorship_visit, NULL quality_score,"
                " NULL critical_met, NULL readiness_class, f.status"
                " FROM dim_facility f WHERE f.iso3=?", (iso3,)))
        operational = [f for f in fac if f["status"] in ("operational", "started_this_period")]
        if fac:
            put("2.3", num=len(operational))
            assessed = [f for f in fac if f["quality_score"] is not None]
            if assessed:
                met = [f for f in assessed
                       if f["quality_score"] >= 80 and f["critical_met"] == "yes"]
                put("2.4", num=len(met), den=len(assessed), unit="rate")
            ready = [f for f in fac if f["readiness_class"] in ("green", "amber", "red")]
            if ready:
                put("2.2", num=len(ready))
                for band in ("green", "amber", "red"):
                    put("2.2", num=len([f for f in ready if f["readiness_class"] == band]),
                        key="readiness_class", val=band)
            ment = [f for f in operational if f["mentorship_visit"] is not None]
            if ment and operational:
                put("3.4", num=len([f for f in ment if f["mentorship_visit"] == 1]),
                    den=len(operational), unit="rate")

        # ---- 3.1: WHO Academy course completions, cumulative
        academy = _sum([ctx.get("who_academy_f"), ctx.get("who_academy_m"), ctx.get("who_academy_ns")])
        if academy is not None:
            put("3.1", num=academy)

        # ---- 3.2: Trainers of Trainers, cumulative by cadre
        tot = list(con.execute(
            "SELECT * FROM fact_workforce_tot WHERE return_id=? AND cadre!='total'", (rid,)))
        tot_trained = _sum([_sum([w["trained_f"], w["trained_m"], w["trained_ns"]]) for w in tot])
        if tot_trained is not None:
            put("3.2", num=tot_trained)

        # ---- 3.3: health workers trained this quarter, by cadre
        wf = list(con.execute(
            "SELECT * FROM fact_workforce WHERE return_id=? AND cadre!='total'", (rid,)))
        trained = _sum([_sum([w["trained_f"], w["trained_m"], w["trained_ns"]]) for w in wf])
        if trained is not None:
            put("3.3", num=trained)

        # ---- 6.1: communication and visibility products
        if ctx.get("comm_products_total") is not None:
            put("6.1", num=ctx["comm_products_total"])

        # ---- 5.1: reporting completeness (HMIS integration is descriptive,
        # not folded into this rate -- see fact_context.his_integration_level
        # and docs/architecture.md)
        q = con.execute("SELECT * FROM fact_quality WHERE return_id=?", (rid,)).fetchone()
        if q and q["facilities_expected"]:
            put("5.1", num=q["returns_complete"], den=q["facilities_expected"], unit="rate")

    con.executemany(
        "INSERT OR REPLACE INTO gold_indicator(iso3,period_id,indicator_code,disagg_key,"
        "disagg_value,numerator,denominator,value,unit,completeness,suppressed,as_of,basis)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    con.execute("DELETE FROM build_manifest")
    periods = [p["period_id"] for p in con.execute(
        "SELECT DISTINCT period_id FROM gold_indicator ORDER BY period_id")]
    con.execute("INSERT INTO build_manifest VALUES (?,?,?,?,?,?)",
                (dt.datetime.now().isoformat(timespec="seconds"), "3.0", "1.0",
                 len(live_returns(con)),
                 con.execute("SELECT COUNT(DISTINCT iso3) n FROM gold_indicator").fetchone()["n"],
                 ",".join(periods)))
    con.commit()
    print(f"gold_indicator: {len(rows)} rows over {len(periods)} periods")
    return con


if __name__ == "__main__":
    build()
