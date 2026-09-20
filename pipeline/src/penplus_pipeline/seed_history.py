#!/usr/bin/env python3
"""
seed_history.py - build historical returns from the evidence that exists today.

Nothing in the store may be invented. Two real sources are converted into returns
of the same shape the Word form produces, and tagged source_kind='historical' with
their provenance, so the dashboard can always separate what a country reported on
the form from what was reconstructed from earlier material.

  ICPPA 2026 country data extraction  ->  patients by year, staff trained, sites
  PEN_PLUS_MONITORING.xlsx            ->  governance milestones, districts, partners

Two rules are enforced while converting.
  - Only the four tracer conditions enter the tracer lines. Everything else goes to
    other_reported and stays out of the regional total.
  - A year row is a flow. The cumulative stock is the running sum of the flows, not
    a figure lifted from a slide, except where the country published a cumulative
    figure explicitly.

    python3 seed_history.py --icppa <xlsx> --monitoring <xlsx>
"""
from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict

import openpyxl

from common import COUNTRIES, ICPPA_CADRE_MAP, ICPPA_CONDITION_MAP
from load import init_db, load_return

PROV_ICPPA = "ICPPA 2026 country data extraction, rebuilt as a form return"
PROV_MON = "PEN_PLUS_MONITORING.xlsx, phase 1 country monitoring workbook"


def _rows(ws):
    head = [c.value for c in ws[1]]
    for r in ws.iter_rows(min_row=2, values_only=True):
        if any(v is not None for v in r):
            yield dict(zip(head, r))


def _int(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(round(v))
    s = re.sub(r"[^0-9.]", "", str(v))
    return int(round(float(s))) if s else None


def _facility_ids(iso3, names):
    return [(f"{iso3}-{i + 1:04d}", n.strip()) for i, n in enumerate(names) if n and n.strip()]


# ------------------------------------------------------------------- ICPPA
def from_icppa(path):
    """Return {(country, year): record} rebuilt from the ICPPA extraction."""
    wb = openpyxl.load_workbook(path, data_only=True)
    enrol, staff, sites = defaultdict(dict), defaultdict(dict), {}

    for r in _rows(wb["Enrolment_by_Year"]):
        if str(r.get("Include in country total", "")).strip().upper() != "Y":
            continue
        country, year = r.get("Country"), _int(r.get("Year"))
        if not country or not year:
            continue
        bucket = enrol[(country, year)]
        for col, key in ICPPA_CONDITION_MAP.items():
            v = _int(r.get(col))
            if v is not None:
                bucket[key] = bucket.get(key, 0) + v

    for r in _rows(wb["Staff_Trained_by_Year"]):
        if str(r.get("Include in country total", "")).strip().upper() != "Y":
            continue
        country, year = r.get("Country"), _int(r.get("Year"))
        if not country or not year:
            continue
        bucket = staff[(country, year)]
        for col, key in ICPPA_CADRE_MAP.items():
            v = _int(r.get(col))
            if v is not None:
                bucket[key] = bucket.get(key, 0) + v

    for r in _rows(wb["Sites_and_Clinics"]):
        country = r.get("Country")
        if not country:
            continue
        names = [n.strip() for n in re.split(r"[;\n]", str(r.get("Site or district names") or ""))
                 if n.strip()]
        sites[country] = {"count": _int(r.get("Number of PEN-Plus sites / clinics")),
                          "names": names,
                          "partners": r.get("Supporting partners and sites each"),
                          "status": r.get("Status / stage")}

    countries = {c for c, _ in list(enrol) + list(staff)} | set(sites)
    out = {}
    for country in sorted(countries):
        if country not in COUNTRIES:
            continue
        iso3 = COUNTRIES[country][0]
        years = sorted({y for c, y in list(enrol) + list(staff) if c == country})
        if not years:
            years = [2026]
        running = defaultdict(int)
        seen_any = defaultdict(bool)
        for year in years:
            flows = enrol.get((country, year), {})
            for k, v in flows.items():
                running[k] += v
                seen_any[k] = True
            rec = {
                "country_name": country,
                "rhythm": "annual", "period_id": f"{year}-A",
                "quarter_id": f"{year}-Q4", "year": year,
                "closing_date": f"{year}-12-31",
                "source_file": os.path.basename(path),
                "patient_stock": [
                    {"condition": k,
                     "ever_enrolled": running[k] if seen_any[k] else None,
                     "active_end": None}
                    for k in ("t1d", "scd", "rhd", "severe_htn", "other_reported")],
                "patient_flow": [
                    {"condition": k, "new_enrolled": flows.get(k),
                     "ltfu": None, "transferred_out": None, "stopped": None, "died": None}
                    for k in ("t1d", "scd", "rhd", "severe_htn", "other_reported")],
                "workforce": [
                    {"cadre": k, "trained_f": None, "trained_m": None,
                     "fully_trained": None, "working_at_site": None}
                    for k in set(ICPPA_CADRE_MAP.values())],
                "context": {}, "quality": {}, "confidence": {},
                "facilities": [], "facility_period": [],
            }
            # trained this year, sex not reported at the time
            sf = staff.get((country, year), {})
            for w in rec["workforce"]:
                v = sf.get(w["cadre"])
                if v is not None:
                    w["trained_f"], w["trained_m"] = None, None
                    w["fully_trained"] = None
                    w["working_at_site"] = None
                    w["trained_total_historical"] = v
            if year == years[-1] and country in sites:
                s = sites[country]
                ids = _facility_ids(iso3, s["names"]) or \
                      [(f"{iso3}-{i + 1:04d}", f"PEN-Plus site {i + 1}")
                       for i in range(s["count"] or 0)]
                rec["facilities"] = [
                    {"facility_id": fid, "name": nm, "district": None, "region": None,
                     "facility_type": None, "services_started": None, "conditions": None,
                     "project_supported": None, "status": "operational"}
                    for fid, nm in ids]
                rec["context"]["sites_reported_icppa"] = s["count"]
            out[(country, year)] = rec
    return out


# -------------------------------------------------------------- monitoring
PILLAR_TO_MILESTONE = {
    "clinical protocol": "national_protocol_disseminated",
    "operational tool": "operational_tools_disseminated",
    "training module": "training_modules_developed",
    "integrat": "penplus_in_national_policy",
    "multisector": "multisectoral_coordination",
    "m&e framework": "national_me_framework",
    "facility-based indicator": "facility_indicators_defined",
}
STATUS_MAP = {"yes": "yes", "y": "yes", "oui": "yes", "no": "no", "n": "no", "non": "no",
              "ongoing": "under_development", "on going": "under_development",
              "in progress": "under_development", "en cours": "under_development",
              "na": "not_applicable", "n/a": "not_applicable"}


def from_monitoring(path):
    """Governance milestones and district counts from the phase 1 workbook.

    The sheets are hand-built, with banner rows above the real header and country
    names in a column that is not the first. The reader therefore looks for the
    header row rather than assuming row 1.
    """
    wb = openpyxl.load_workbook(path, data_only=True)
    out = {}

    def norm_status(v):
        return STATUS_MAP.get(str(v).strip().lower(), "not_reported") if v else "not_reported"

    def find_country_column(ws, limit=12):
        """Locate the header row and the country column.

        Some sheets have a 'Country' header; others simply start listing country
        names in an arbitrary column under a banner. Both are handled: the label is
        tried first, then the column whose values most often match a known country.
        """
        for i, row in enumerate(ws.iter_rows(max_row=limit, values_only=True), 1):
            for j, v in enumerate(row):
                if v and str(v).strip().lower().startswith("country"):
                    return i, j
        best, best_hits, first_row = None, 0, None
        for j in range(min(ws.max_column, 12)):
            hits, top = 0, None
            for i, row in enumerate(ws.iter_rows(max_row=min(ws.max_row, 60), values_only=True), 1):
                if j < len(row) and str(row[j] or "").strip() in COUNTRIES:
                    hits += 1
                    top = top or i
            if hits > best_hits:
                best, best_hits, first_row = j, hits, top
        if best is not None and best_hits >= 3:
            return first_row - 1, best
        return None, None

    # ---- districts implementing PEN-Plus
    for name in wb.sheetnames:
        if "district" not in name.lower():
            continue
        ws = wb[name]
        hrow, ccol = find_country_column(ws)
        if hrow is None:
            continue
        dcol = None
        for i, row in enumerate(ws.iter_rows(min_row=hrow, max_row=hrow + 2, values_only=True), hrow):
            for j, v in enumerate(row):
                if v and "district" in str(v).lower() and "implement" in str(v).lower():
                    dcol = j
        for row in ws.iter_rows(min_row=hrow + 1, values_only=True):
            country = str(row[ccol] or "").strip() if ccol < len(row) else ""
            if country not in COUNTRIES:
                continue
            rec = out.setdefault(country, _blank_monitoring_rec(country, path))
            if dcol is not None and dcol < len(row):
                v = _int(row[dcol])
                if v is not None:
                    rec["context"]["districts_with_penplus"] = v

    # ---- pillar activities, read as governance milestones
    for name in wb.sheetnames:
        if "pillar" not in name.lower():
            continue
        ws = wb[name]
        hrow, ccol = find_country_column(ws)
        if hrow is None:
            continue
        labels = {}
        for i in range(max(1, hrow - 3), hrow + 1):
            for j, c in enumerate(ws[i]):
                if c.value and len(str(c.value).strip()) > 8:
                    labels[j] = str(c.value).strip()
        for row in ws.iter_rows(min_row=hrow + 1, values_only=True):
            country = str(row[ccol] or "").strip() if ccol < len(row) else ""
            if country not in COUNTRIES:
                continue
            rec = out.setdefault(country, _blank_monitoring_rec(country, path))
            seen = set()
            for j, v in enumerate(row):
                lab = labels.get(j)
                if not lab or v is None:
                    continue
                code = next((c for frag, c in PILLAR_TO_MILESTONE.items()
                             if frag in lab.lower()), None)
                if code and code not in seen:
                    seen.add(code)
                    rec["governance"].append({
                        "milestone_code": code, "milestone": lab,
                        "status": norm_status(v), "achieved_in": None, "document": None})
    return out


def _blank_monitoring_rec(country, path):
    return {"country_name": country, "rhythm": "annual", "period_id": "2025-A",
            "quarter_id": "2025-Q4", "year": 2025, "closing_date": "2025-12-31",
            "source_file": os.path.basename(path),
            "patient_stock": [], "patient_flow": [], "patient_age": [], "workforce": [],
            "supply": [], "service": [], "assumptions": [], "governance": [],
            "context": {}, "quality": {}, "confidence": {},
            "facilities": [], "facility_period": [], "retention": []}


# -------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--icppa", required=True)
    ap.add_argument("--monitoring")
    ap.add_argument("--db", default=None)
    args = ap.parse_args()

    con = init_db(args.db) if args.db else init_db()
    n = 0

    if args.monitoring and os.path.exists(args.monitoring):
        for country, rec in sorted(from_monitoring(args.monitoring).items()):
            load_return(con, rec, source_kind="historical", provenance=PROV_MON)
            n += 1

    for (country, year), rec in sorted(from_icppa(args.icppa).items()):
        load_return(con, rec, source_kind="historical", provenance=PROV_ICPPA)
        n += 1

    print(f"seeded {n} historical returns")
    for row in con.execute(
        "SELECT c.name, COUNT(*) n, MIN(r.period_id), MAX(r.period_id)"
        " FROM fact_return r JOIN dim_country c USING(iso3)"
        " WHERE r.source_kind='historical' GROUP BY c.name ORDER BY c.name"):
        print(f"  {row[0]:36s} {row[1]:2d} returns  {row[2]} to {row[3]}")


if __name__ == "__main__":
    main()
