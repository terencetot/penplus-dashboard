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

from common import OTHER_CONDITIONS, SENTINEL_SUM, TRACERS
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


#: The indicators a patient query concerns. The query register predates the
#: new tool's split of patients into 2.5 / 2.6, so a query on either patient
#: code holds every patient figure for that country.
PATIENT_CODES = ("2.5", "2.6", "2.6a", "2.6b")


def _codes_for(indicator: str | None) -> set[str]:
    parts = {p.strip() for p in (indicator or "").replace(",", "/").split("/") if p.strip()}
    if parts & set(PATIENT_CODES):
        parts |= set(PATIENT_CODES)
    return parts


def query_holds(con) -> dict[tuple[str, str], str]:
    """{(iso3, indicator_code): query ids} for every OPEN High query.

    An open High query holds the figure it concerns: the figure stays in the
    bundle, marked held, and out of every regional total (DATA_QUALITY_SPEC.md
    section 4.4). Regional-scope queries ('REG') are applied in export.py,
    where the regional figure itself is built.
    """
    holds: dict[tuple[str, str], str] = {}
    for q in con.execute("SELECT * FROM fact_query WHERE status='open' AND severity='High'"):
        for iso3 in (x.strip() for x in q["scope"].split(";")):
            if not iso3 or iso3 == "REG":
                continue
            for code in _codes_for(q["indicator"]):
                key = (iso3, code)
                holds[key] = f"{holds[key]}, {q['query_id']}" if key in holds else q["query_id"]
    return holds


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
    holds = query_holds(con)

    for r in live_returns(con):
        rid, iso3, pid = r["return_id"], r["iso3"], r["period_id"]
        comp, as_of = r["completeness"], r["closing_date"]
        basis = r["source_kind"]

        # iso3/pid/comp/as_of/basis are bound as defaults, not read by closure,
        # so each redefinition of put() (once per return, every loop pass)
        # freezes that return's own values -- put() is always fully used
        # within the same iteration it's defined in, never deferred.
        src = {(v["indicator_code"], v["disagg_value"]): v for v in con.execute(
            "SELECT * FROM fact_value_source WHERE return_id=?", (rid,))}

        def put(code, num=None, den=None, unit="count", key="all", val="all", value=None,
                *, iso3=iso3, pid=pid, comp=comp, as_of=as_of, basis=basis, src=src):
            v = value if value is not None else (num if unit == "count" else _rate(num, den))
            prov = src.get((code, val)) or src.get((code, "all"))
            hold = holds.get((iso3, code))
            rows.append((iso3, pid, code, key, val, num, den, v, unit, comp,
                         1 if (num is not None and num < SUPPRESS_BELOW and unit == "count"
                               and key != "all") else 0,
                         as_of, basis, prov["value_type"] if prov else None,
                         prov["source_ref"] if prov else None,
                         1 if hold else 0, hold))

        # ---- 2.5, 2.6, 2.6a, 2.6b: patients (new national tool definitions)
        stock = {s["condition"]: s for s in con.execute(
            "SELECT * FROM fact_patient_stock WHERE return_id=?", (rid,))}
        flow = {f["condition"]: f for f in con.execute(
            "SELECT * FROM fact_patient_flow WHERE return_id=?", (rid,))}
        # fact_context holds everything sourced from a single Item/Response
        # cell rather than a per-condition or per-cadre table: read it once.
        ctx = {c["measure"]: c["value"] for c in con.execute(
            "SELECT measure,value FROM fact_context WHERE return_id=?", (rid,))}

        sentinel = [c for c in SENTINEL_SUM if c in stock]
        ever = _sum(stock[c]["ever_enrolled"] for c in sentinel)
        active = _sum(stock[c]["active_end"] for c in sentinel)
        new = _sum(flow[c]["new_enrolled"] for c in sentinel if c in flow)
        if sentinel:
            # A null here is "returned, not reported" and stays null.
            put("2.6", num=ever)
            put("2.6a", num=active)
        if new is not None:
            put("2.6", num=new, key="measure", val="new_this_period")
        for c in sentinel:
            if stock[c]["ever_enrolled"] is not None:
                put("2.6", num=stock[c]["ever_enrolled"], key="condition", val=c)
            if stock[c]["active_end"] is not None:
                put("2.6a", num=stock[c]["active_end"], key="condition", val=c)
        # Conditions outside the sentinel set (severe hypertension since Sept
        # 2026, and anything else a country reports) stay visible as 2.5
        # condition rows but never enter a sentinel total.
        for c in OTHER_CONDITIONS:
            if c in stock and stock[c]["ever_enrolled"] is not None:
                put("2.5", num=stock[c]["ever_enrolled"], key="condition", val=c)

        # 2.5 is the country's own all-conditions total. It is never rebuilt
        # by adding condition columns: which extra conditions a country
        # counts as PEN-Plus is the country's definition, not ours.
        if ctx.get("patients_all_ever") is not None:
            put("2.5", num=ctx["patients_all_ever"])
        if ctx.get("patients_all_new") is not None:
            put("2.5", num=ctx["patients_all_new"], key="measure", val="new_this_period")
        if ctx.get("patients_all_active") is not None:
            put("2.5", num=ctx["patients_all_active"], key="measure", val="active")

        # 2.6b: approximate retention, computed here and never read from the
        # form (its printed formula divides by patients no longer in care).
        # Quarterly form returns only: "newly enrolled this quarter" has no
        # meaning in a yearly baseline row.
        # Only conditions with all three figures enter it, so a condition
        # missing one of them cannot push the ratio above 100%.
        if basis == "form":
            complete = [c for c in sentinel if c in flow and None not in (
                stock[c]["ever_enrolled"], stock[c]["active_end"], flow[c]["new_enrolled"])]
            r_num = _sum(stock[c]["active_end"] - flow[c]["new_enrolled"] for c in complete)
            r_den = _sum(stock[c]["ever_enrolled"] - flow[c]["new_enrolled"] for c in complete)
            if r_num is not None and r_den and r_den > 0:
                put("2.6b", num=r_num, den=r_den, unit="rate")

        for a in con.execute(
                "SELECT age_band, SUM(patients) n FROM fact_patient_age"
                " WHERE return_id=? AND condition!='total' GROUP BY age_band", (rid,)):
            if a["age_band"] != "total":
                put("2.6a", num=a["n"], key="age_band", val=a["age_band"])

        # ---- 2.1: guideline dissemination, tracers only. The denominator is
        # how many conditions this return actually answered, not a hard-coded
        # constant -- the current form asks about three priority conditions,
        # the previous copy asked about four, and a historical return might
        # answer fewer still. Hard-coding TRACERS' own length here would
        # silently misstate the rate the moment the form's condition list
        # changes again.
        disseminated = [ctx.get(f"guideline_disseminated_{c}") for c in TRACERS]
        reported = [v for v in disseminated if v is not None]
        if reported:
            put("2.1", num=sum(1 for v in reported if v == 1), den=len(reported), unit="rate")

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
        if trained is None:
            trained = ctx.get("trained_hist")      # ICPPA baseline: trained in that year
        if trained is not None:
            put("3.3", num=trained)
        # Health workers trained since the programme began in the country:
        # the running sum of the yearly flows, or a cumulative figure the
        # country published as such -- built in seed_history, never by adding
        # a stock to itself.
        if ctx.get("trained_hist_to_date") is not None:
            put("3.3", num=ctx["trained_hist_to_date"], key="measure", val="to_date")

        # ---- 6.1: communication and visibility products
        if ctx.get("comm_products_total") is not None:
            put("6.1", num=ctx["comm_products_total"])

        # ---- 5.2: PEN-Plus indicators integrated into the HMIS / DHIS2.
        # 2 = Yes, 1 = Partial, 0 = No (parse.py). Only Yes counts; Partial is
        # published as its own response row so it is seen, not rounded up.
        his = ctx.get("his_integration_level")
        if his is not None:
            put("5.2", num=1 if his == 2 else 0)
            put("5.2", num=1, key="response", val={2: "yes", 1: "partial", 0: "no"}[his])

    con.executemany(
        "INSERT OR REPLACE INTO gold_indicator(iso3,period_id,indicator_code,disagg_key,"
        "disagg_value,numerator,denominator,value,unit,completeness,suppressed,as_of,basis,"
        "value_type,source_ref,held,held_by)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

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
