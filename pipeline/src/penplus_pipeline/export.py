#!/usr/bin/env python3
"""
export.py - write the static JSON bundle the dashboard reads.

One file per screen, plus a manifest. The bundle is the API: the site makes no
network call beyond loading these files, and performs no calculation on them.
Every count, share, total and split a screen shows is computed here.

Held figures (an open High query, or a High validation failure) are published
marked held and kept out of every regional total. A country is counted as
reporting an indicator only for a non-null value.
"""
from __future__ import annotations

import json
import os

from common import IMPLEMENTATION_STEPS, PUBLISH_FACILITY_NAMES
from load import DB_DEFAULT, connect
from transform import _codes_for
from validate import RULES

HERE = os.path.dirname(os.path.abspath(__file__))
# HERE = <repo>/pipeline/src/penplus_pipeline -> <repo>/site/public/data
# The bundle lives under site/public so Vite serves and copies it verbatim;
# the built site still exposes it at /data, matching the specification.
OUT_DEFAULT = os.path.join(HERE, "..", "..", "..", "site", "public", "data")

#: The sixteen Results Framework indicators of the new national tool. 2.6a
#: (sentinel active) and 2.6b (approximate retention) are published alongside
#: 2.6, not as indicators of their own: the coverage matrix counts sixteen.
CORE_INDICATORS = ["1.1", "1.2", "1.3", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6",
                   "3.1", "3.2", "3.3", "3.4", "4.1", "5.2", "6.1"]
SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def _d(rows):
    return [dict(r) for r in rows]


def _redact_facility(f: dict) -> dict:
    """Facility identity withheld (only when PUBLISH_FACILITY_NAMES is off)."""
    f = dict(f)
    for k in ("name", "district", "region", "town"):
        f[k] = None
    return f


def _redact_suppressed_gold(g: dict) -> dict:
    """CLAUDE.md rule 7: a numerator under five is withheld in the public
    export, not just flagged. The internal export keeps the real number."""
    if not g["suppressed"]:
        return g
    g = dict(g)
    g["numerator"] = None
    g["denominator"] = None
    g["value"] = None
    return g


def coverage_pct(reporting, total):
    """Share of countries with a published figure, as a whole per cent --
    computed here so a "Partial · NN%" badge is never a division the browser
    performs (CLAUDE.md rule 1)."""
    return round(reporting / total * 100) if total else None


def export(db_path: str = DB_DEFAULT, out_dir: str = OUT_DEFAULT, public: bool = False):
    con = connect(db_path)
    out = os.path.abspath(out_dir)
    os.makedirs(os.path.join(out, "countries"), exist_ok=True)

    form_returns = con.execute(
        "SELECT COUNT(*) n FROM fact_return WHERE superseded=0 AND source_kind='form'"
        " AND verdict IN ('accepted','query')").fetchone()["n"]
    man = dict(con.execute("SELECT * FROM build_manifest").fetchone())
    man["suppress_below"] = 5
    man["public"] = public
    man["publish_facility_names"] = PUBLISH_FACILITY_NAMES
    # While no validated second-round return exists, every screen says the
    # figures are the ICPPA 2026 baseline (audit v2, section 4).
    man["baseline_only"] = form_returns == 0
    man["form_returns"] = form_returns
    man["note"] = ("Values are pre-computed. null means not reported and is never zero. "
                   "basis='historical' marks the ICPPA 2026 baseline (country presentations,"
                   " June 2026), not a validated quarterly return. held=1 marks a figure held"
                   " by an open High query; it is excluded from every regional total."
                   + (" Cells under 5 are suppressed, not merely flagged." if public else ""))

    phases = {r["iso3"]: dict(r) for r in con.execute("SELECT * FROM fact_phase")}
    countries = _d(con.execute(
        "SELECT c.iso3, c.name, c.cohort,"
        " (SELECT COUNT(*) FROM fact_return r WHERE r.iso3=c.iso3 AND r.superseded=0) returns,"
        " (SELECT MAX(period_id) FROM fact_return r WHERE r.iso3=c.iso3 AND r.superseded=0) last_period,"
        " (SELECT COUNT(*) FROM gold_indicator g WHERE g.iso3=c.iso3 AND g.value IS NOT NULL"
        "   AND g.disagg_key='all') n_values,"
        " (SELECT COUNT(*) FROM fact_return r WHERE r.iso3=c.iso3 AND r.superseded=0"
        "   AND r.source_kind='form') form_returns"
        " FROM dim_country c ORDER BY c.name"))
    for c in countries:
        c["has_data"] = c.pop("n_values") > 0
        c["phase"] = (phases.get(c["iso3"]) or {}).get("phase_to_publish")
    n_countries = len(countries)

    indicators = _d(con.execute("SELECT * FROM dim_indicator ORDER BY indicator_code"))
    gold = _d(con.execute("SELECT * FROM gold_indicator"))
    queries = _d(con.execute("SELECT * FROM fact_query ORDER BY query_id"))
    open_queries = [q for q in queries if q["status"] == "open"]

    # Regional holds: an open High query scoped to the region holds the
    # regional figure of the indicator(s) it concerns (Q-REG-01: no regional
    # patient headline until one figure and its scope are agreed).
    regional_hold: dict[str, list[str]] = {}
    for q in open_queries:
        if q["severity"] == "High" and "REG" in [s.strip() for s in q["scope"].split(";")]:
            for code in _codes_for(q["indicator"]):
                regional_hold.setdefault(code, []).append(q["query_id"])

    latest = {}
    latest_dis = {}
    for g in gold:
        k = (g["iso3"], g["indicator_code"], g["disagg_key"], g["disagg_value"])
        target = latest if g["disagg_key"] == "all" else latest_dis
        if k not in target or g["period_id"] > target[k]["period_id"]:
            target[k] = g

    def regional(code, unit="count", key="all", val="all"):
        """The one regional figure for an indicator: sum of numerators for a
        count, sum(num)/sum(den) for a rate, over each country's latest
        non-null, non-held value. Held figures are counted apart."""
        src = latest if key == "all" else latest_dis
        rows = [v for (i, c, k, d), v in src.items() if c == code and k == key and d == val]
        live = [v for v in rows if v["value"] is not None and not v["held"]]
        held = [v for v in rows if v["value"] is not None and v["held"]]
        as_of = max((v["as_of"] for v in live if v["as_of"]), default=None)
        if unit == "rate":
            nums = [v["numerator"] for v in live if v["numerator"] is not None]
            dens = [v["denominator"] for v in live if v["denominator"] is not None]
            value = (sum(nums) / sum(dens)) if (nums and dens and sum(dens) > 0) else None
        else:
            nums = [v["numerator"] for v in live if v["numerator"] is not None]
            value = sum(nums) if nums else None
        hold = regional_hold.get(code, [])
        return {
            "total": None if hold else value,
            "total_held_by": ", ".join(hold) or None,
            "as_of": as_of,
            "countries_reporting": len(live),
            "countries_held": len(held),
            "held_by": sorted({v["held_by"] for v in held if v["held_by"]}),
            "countries_total": n_countries,
            "coverage_pct": coverage_pct(len(live), n_countries),
            "basis": "historical" if live and all(v["basis"] == "historical" for v in live)
                     else ("form" if live else None),
        }

    for dim in indicators:
        r = regional(dim["indicator_code"], dim["unit"])
        dim["regional_value"] = r["total"]
        dim["regional_held_by"] = r["total_held_by"]
        dim["regional_as_of"] = r["as_of"]
        dim["countries_reporting"] = r["countries_reporting"]
        dim["countries_held"] = r["countries_held"]
        dim["countries_without"] = n_countries - r["countries_reporting"]
        dim["countries_total"] = n_countries
        dim["coverage_pct"] = r["coverage_pct"]
        dim["gap"] = (dim["milestone"] - r["total"]) \
            if (dim["milestone"] is not None and r["total"] is not None) else None
        # value types used across the latest country values, for the label
        # next to a patient figure ("ever enrolled", "active", "as of ...")
        dim["value_types"] = sorted({v["value_type"] for (i, c, k, d), v in latest.items()
                                     if c == dim["indicator_code"] and v["value_type"]})

    headline = {
        "facilities": regional("2.3"),
        "sentinel_ever": regional("2.6"),
        "all_ever": regional("2.5"),
        "sentinel_active": regional("2.6a"),
        "trained": regional("3.3", key="measure", val="to_date"),
    }

    HEADLINE_INDICATORS = ["2.3", "2.5", "2.6", "3.3", "2.4"]
    ind_by_code = {i["indicator_code"]: i for i in indicators}
    milestone_strip = [{
        "indicator_code": code,
        "label_en": ind_by_code[code]["label_en"],
        "unit": ind_by_code[code]["unit"],
        "value": (headline["trained"]["total"] if code == "3.3"
                  else ind_by_code[code]["regional_value"]),
        "held_by": ind_by_code[code]["regional_held_by"],
        "as_of": ind_by_code[code]["regional_as_of"],
        "milestone": ind_by_code[code]["milestone"],
        "gap": ind_by_code[code]["gap"],
        "countries_reporting": (headline["trained"]["countries_reporting"] if code == "3.3"
                                else ind_by_code[code]["countries_reporting"]),
        "countries_total": n_countries,
    } for code in HEADLINE_INDICATORS if code in ind_by_code]

    def write(name, obj):
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)

    gold_out = [_redact_suppressed_gold(g) for g in gold] if public else gold
    latest_out = [_redact_suppressed_gold(v) for v in latest.values()] if public \
        else list(latest.values())

    write("manifest.json", man)
    # ---- situation by country: one row per country, alphabetical (never a
    # ranking), every figure and every bar length computed here.
    def latest_val(iso3, code, key="all", val="all"):
        src = latest if key == "all" else latest_dis
        return src.get((iso3, code, key, val))

    fac_active = {}
    for f in con.execute("SELECT iso3, COUNT(*) n FROM dim_facility WHERE status='operational'"
                         " GROUP BY iso3"):
        fac_active[f["iso3"]] = f["n"]
    table = []
    for c in countries:
        pat = latest_val(c["iso3"], "2.6")
        allp = latest_val(c["iso3"], "2.5")
        tr = latest_val(c["iso3"], "3.3", "measure", "to_date")
        act = latest_val(c["iso3"], "2.6a")
        table.append({
            "iso3": c["iso3"], "name": c["name"], "cohort": c["cohort"], "phase": c["phase"],
            "facilities": fac_active.get(c["iso3"]),
            "patients": pat["value"] if pat and pat["value"] is not None else None,
            "patients_held": bool(pat and pat["held"]),
            "patients_all": allp["value"] if allp and allp["value"] is not None else None,
            "trained": tr["value"] if tr and tr["value"] is not None else None,
            "patients_active": act["value"] if act and act["value"] is not None else None,
            "latest_period": c["last_period"] if c["has_data"] else None,
        })
    for key in ("facilities", "patients", "patients_all", "trained"):
        top = max((r[key] for r in table if r[key] is not None
                   and not (key == "patients" and r["patients_held"])), default=None)
        for r in table:
            held = key == "patients" and r["patients_held"]
            r[f"{key}_bar"] = (round(r[key] / top * 100)
                               if (top and r[key] is not None and not held) else None)
    phase45 = sum(1 for c in countries if c["phase"] in (4, 5))
    with_phase = sum(1 for c in countries if c["phase"] is not None)

    write("overview.json", {
        "manifest": man,
        "headline": headline,
        "country_table": table,
        "programme": {
            "countries": n_countries,
            "round1": sum(1 for c in countries if c["cohort"] == "phase_1"),
            "round2": sum(1 for c in countries if c["cohort"] == "phase_2"),
            "phase45": phase45,
            "with_phase": with_phase,
        },
        "milestone_strip": milestone_strip,
        "countries": countries,
        "countries_with_data": sum(1 for c in countries if c["has_data"]),
        "latest": latest_out,
    })
    write("indicators.json", {"manifest": man, "dim": indicators, "values": gold_out})

    # ------------------------------------------------------------ data quality
    checks = _d(con.execute("SELECT * FROM fact_check"))
    returns = _d(con.execute(
        "SELECT r.*, p.closing_date FROM fact_return r JOIN dim_period p USING(period_id)"
        " WHERE r.superseded=0 ORDER BY r.iso3, r.period_id"))
    latest_return = {}
    for r in returns:
        latest_return[r["iso3"]] = r

    def queries_for(iso3):
        return [q for q in queries if iso3 in [s.strip() for s in q["scope"].split(";")]]

    provenance = []
    for c in countries:
        r = latest_return.get(c["iso3"])
        oq = [q for q in queries_for(c["iso3"]) if q["status"] == "open"]
        held_here = any(v["held"] for (i, *_), v in latest.items() if i == c["iso3"])
        vtypes = sorted({v["value_type"] for (i, *_), v in latest.items()
                         if i == c["iso3"] and v["value_type"]})
        if not r or not c["has_data"]:
            source, status = "none", "no_return"
        elif r["source_kind"] == "form":
            source = "form"
            status = "held" if (r["verdict"] == "hold" or held_here) else "validated"
        else:
            source = "historical"
            status = "held" if held_here else "historical"
        provenance.append({
            "iso3": c["iso3"], "name": c["name"], "cohort": c["cohort"],
            "evidence_source": source, "latest_period": r["period_id"] if r and c["has_data"] else None,
            "value_types": vtypes, "open_queries": len(oq),
            "highest_severity": min((q["severity"] for q in oq),
                                    key=lambda s: SEVERITY_ORDER[s], default=None),
            "status": status,
        })

    coverage_rows = []
    for c in countries:
        cells = {}
        for code in CORE_INDICATORS:
            v = latest.get((c["iso3"], code, "all", "all"))
            if code == "3.3" and (v is None or v["value"] is None):
                v = latest_dis.get((c["iso3"], "3.3", "measure", "to_date"))
            if v is None or v["value"] is None:
                cells[code] = "not_reported"
            else:
                cells[code] = "held" if v["held"] else "value"
        coverage_rows.append({"iso3": c["iso3"], "name": c["name"], "cells": cells})
    coverage_by_indicator = []
    for code in CORE_INDICATORS:
        n_val = sum(1 for r in coverage_rows if r["cells"][code] == "value")
        coverage_by_indicator.append({
            "indicator_code": code,
            "label_en": ind_by_code[code]["label_en"] if code in ind_by_code else code,
            "countries_with_value": n_val,
            "countries_held": sum(1 for r in coverage_rows if r["cells"][code] == "held"),
            "coverage_pct": coverage_pct(n_val, n_countries)})

    check_summary = []
    for rule, (sev, what, _ind) in RULES.items():
        rows = [c for c in checks if c["rule"] == rule]
        check_summary.append({
            "rule": rule, "severity": sev, "check": what,
            "passed": sum(1 for c in rows if c["outcome"] == "passed"),
            "failed": sum(1 for c in rows if c["outcome"] == "failed"),
            "not_testable": sum(1 for c in rows if c["outcome"] == "not_testable"),
            "failures": [{"iso3": c["iso3"], "period_id": c["period_id"], "detail": c["detail"]}
                         for c in rows if c["outcome"] == "failed"],
        })

    held_figures = [{"iso3": v["iso3"], "indicator_code": v["indicator_code"],
                     "period_id": v["period_id"], "value": v["value"], "held_by": v["held_by"]}
                    for v in latest.values() if v["held"] and v["value"] is not None]
    held_regional = [{"indicator_code": code, "held_by": ", ".join(ids)}
                     for code, ids in sorted(regional_hold.items())
                     if code in ind_by_code]

    period_latest_form = max((r["period_id"] for r in returns if r["source_kind"] == "form"),
                             default=None)
    validated_latest = sum(1 for r in returns if r["source_kind"] == "form"
                           and r["period_id"] == period_latest_form and r["verdict"] != "hold")

    dsa_rows = _d(con.execute("SELECT * FROM fact_dsa ORDER BY iso3, field"))
    dsa = {}
    for r in dsa_rows:
        e = dsa.setdefault(r["iso3"], {"iso3": r["iso3"], "assessed_on": r["assessed_on"],
                                       "institution": r["institution"], "fields": {}})
        e["fields"][r["field"]] = r["response"]
    name_of = {c["iso3"]: c["name"] for c in countries}
    for e in dsa.values():
        e["name"] = name_of.get(e["iso3"])

    write("quality.json", {
        "manifest": man,
        "kpis": {
            "validated_returns": {"n": validated_latest, "total": n_countries,
                                  "period": period_latest_form},
            "held_figures": {"n": len(held_figures), "regional": len(held_regional)},
            "open_queries": {"total": len(open_queries),
                             **{s: sum(1 for q in open_queries if q["severity"] == s)
                                for s in ("High", "Medium", "Low")}},
            "queries_closed": sum(1 for q in queries if q["status"] == "closed"),
            "indicators_covered": {
                "n": sum(1 for i in coverage_by_indicator if (i["coverage_pct"] or 0) >= 80),
                "total": len(CORE_INDICATORS)},
        },
        "provenance": provenance,
        "coverage": {"indicators": coverage_by_indicator, "rows": coverage_rows},
        "checks": check_summary,
        "held_figures": held_figures,
        "held_regional": held_regional,
        "queries": queries,
        "data_systems": sorted(dsa.values(), key=lambda e: e["name"] or e["iso3"]),
        "data_systems_missing": [c["name"] for c in countries if c["iso3"] not in dsa],
    })

    # -------------------------------------------------------------- facilities
    facility_rows = _d(con.execute(
        "SELECT f.*, c.name country FROM dim_facility f JOIN dim_country c USING(iso3)"
        " ORDER BY c.name, f.facility_id"))
    for f in facility_rows:
        # On the map only when every geocoding rule passed or a person checked it.
        has_point = f["latitude"] is not None and f["longitude"] is not None
        # The facility's own point: OSM rules passed (auto), a person checked
        # it (yes), or it is in the WHO/KEMRI facility list (dataset).
        f["mapped"] = bool(has_point and f["geo_checked"] in ("yes", "auto", "dataset"))
        # A town point, shown on the map as approximate, never as the facility.
        f["approximate"] = bool(has_point and f["geo_checked"] == "approximate")
    if public and not PUBLISH_FACILITY_NAMES:
        facility_rows = [_redact_facility(f) for f in facility_rows]
    by_status = {}
    for f in facility_rows:
        by_status[f["register_status"] or "unknown"] = by_status.get(f["register_status"] or "unknown", 0) + 1
    by_country = {}
    for f in facility_rows:
        e = by_country.setdefault(f["iso3"], {"iso3": f["iso3"], "country": f["country"],
                                              "total": 0, "mapped": 0, "approximate": 0})
        e["total"] += 1
        e["mapped"] += 1 if f["mapped"] else 0
        e["approximate"] += 1 if f["approximate"] else 0
        e["off_map"] = e.get("off_map", 0) + (0 if (f["mapped"] or f["approximate"]) else 1)
    write("facilities.json", {
        "manifest": man,
        "by_country": sorted(by_country.values(), key=lambda e: e["country"]),
        "kpis": {
            "total": len(facility_rows),
            "active": by_status.get("active", 0),
            "by_status": by_status,
            "countries": len({f["iso3"] for f in facility_rows}),
            "mapped": sum(1 for f in facility_rows if f["mapped"]),
            "approximate": sum(1 for f in facility_rows if f["approximate"]),
            "on_map": sum(1 for f in facility_rows if f["mapped"] or f["approximate"]),
            "location_to_confirm": sum(1 for f in facility_rows
                                       if not f["mapped"] and not f["approximate"]),
            "names_to_confirm": sum(1 for f in facility_rows if f["name_status"] == "to_confirm"),
        },
        "rows": facility_rows})

    # --------------------------------------------------- implementation phases
    step_dim = [{"step_no": s, "phase_no": p, "phase_label": pl, "step_label": sl}
                for s, p, pl, sl in IMPLEMENTATION_STEPS]
    impl_by_country: dict[str, dict] = {}
    for r in _d(con.execute("SELECT * FROM fact_implementation_step")):
        impl_by_country.setdefault(r["iso3"], {})[r["step_no"]] = r

    def country_implementation(iso3: str) -> dict:
        by_step = impl_by_country.get(iso3, {})
        ph = phases.get(iso3) or {}
        return {
            "phase": ph.get("phase_to_publish"),
            "workbook_phase": ph.get("workbook_phase"),
            "icppa_map_phase": ph.get("icppa_map_phase"),
            "agreement": ph.get("agreement"),
            "note": ph.get("note"),
            "source": ph.get("source"),
            "has_steps": bool(by_step),
            "steps": [
                {"step_no": s["step_no"],
                 "status": by_step.get(s["step_no"], {}).get("status"),
                 "source": by_step.get(s["step_no"], {}).get("source"),
                 "as_of": by_step.get(s["step_no"], {}).get("as_of")}
                for s in step_dim
            ],
        }

    impl_countries = [{"iso3": c["iso3"], "name": c["name"], "cohort": c["cohort"],
                       **country_implementation(c["iso3"])} for c in countries]
    phase_counts = [{"phase": p, "countries": sum(1 for c in impl_countries if c["phase"] == p)}
                    for p in (5, 4, 3, 2, 1)]
    write("implementation.json", {
        "manifest": man,
        "steps": step_dim,
        "phase_counts": phase_counts,
        "no_return": sum(1 for c in impl_countries if c["phase"] is None),
        "with_phase": sum(1 for c in impl_countries if c["phase"] is not None),
        "disagreements": sum(1 for c in impl_countries if c["agreement"] == "no"),
        "countries": impl_countries,
    })

    for c in countries:
        iso3 = c["iso3"]
        country_gold = [g for g in gold if g["iso3"] == iso3]
        country_facilities = [f for f in facility_rows if f["iso3"] == iso3]
        if public:
            country_gold = [_redact_suppressed_gold(g) for g in country_gold]
        write(f"countries/{iso3}.json", {
            "manifest": man, "country": c,
            "values": country_gold,
            "facilities": country_facilities,
            "implementation": country_implementation(iso3),
            "provenance": next(p for p in provenance if p["iso3"] == iso3),
            # One row per milestone_code: its most recent period.
            "governance": _d(con.execute(
                "SELECT g.*, r.period_id FROM fact_governance g JOIN fact_return r USING(return_id)"
                " WHERE r.iso3=? AND r.superseded=0 AND g.milestone_code NOT LIKE '2.1-%'"
                " AND g.milestone_code != '4.1'"
                " AND r.period_id = ("
                "   SELECT MAX(r2.period_id) FROM fact_governance g2"
                "   JOIN fact_return r2 USING(return_id)"
                "   WHERE r2.iso3=r.iso3 AND r2.superseded=0 AND g2.milestone_code=g.milestone_code"
                " )"
                " ORDER BY g.milestone_code", (iso3,))),
            "queries": queries_for(iso3),
            "data_system": dsa.get(iso3),
        })

    total = sum(os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(out) for f in fs)
    print(f"bundle written to {out}: {total/1024:.0f} KB")


if __name__ == "__main__":
    export()
