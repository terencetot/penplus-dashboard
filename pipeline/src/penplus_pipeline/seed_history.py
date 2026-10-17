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
  - Only the three sentinel conditions (T1D, SCD, RHD) enter a sentinel total.
    Severe hypertension and everything else keep their own condition rows.
  - The workbook's "Value type" column decides how a row is read: a flow row is
    new enrolment in the year (ever enrolled is the running sum); a cumulative,
    active or point-in-time row is a stock and is never added across years.

    python3 seed_history.py --icppa <xlsx> --monitoring <xlsx>
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
from collections import defaultdict

import openpyxl
from common import (
    COUNTRIES,
    ICPPA_CADRE_MAP,
    ICPPA_CONDITION_MAP,
    IMPLEMENTATION_STEPS,
    SENTINEL_SUM,
)
from load import init_db, load_return

PROV_ICPPA = "ICPPA 2026 country data extraction, rebuilt as a form return"
PROV_MON = "PEN_PLUS_MONITORING.xlsx, phase 1 country monitoring workbook"


def _closing_date_for_year(year: int) -> str:
    """The annual period's closing date: 31 December for a year that has
    fully elapsed, or today for the current, still-incomplete year, since the
    source workbooks record no cut-off finer than a year. Stamping 31
    December on a year still in progress publishes evidence that does not yet
    exist -- see docs/architecture.md, "Data integrity"."""
    dec_31 = dt.date(year, 12, 31)
    today = dt.date.today()
    return min(dec_31, today).isoformat()


def _rows(ws):
    head = [c.value for c in ws[1]]
    for r in ws.iter_rows(min_row=2, values_only=True):
        if any(v is not None for v in r):
            # Not strict: these are hand-built workbooks and a data row
            # running longer or shorter than the header is expected, not an
            # error -- zip's default truncation is the intended behaviour.
            yield dict(zip(head, r))  # noqa: B905


def _int(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(round(v))
    s = re.sub(r"[^0-9.]", "", str(v))
    return int(round(float(s))) if s else None


# ------------------------------------------------------------------- ICPPA
def source_ref(document, slide) -> str | None:
    """'Slide_Deck_-_Day_3_-_Main_room.pptx', 224 -> 'D3M p224'.

    The short form the evidence pack uses for its slide images
    (docs/refinement/06_evidence_slides/D3M_p224_...png)."""
    if not document:
        return None
    d = str(document).lower()
    day = re.search(r"day_(\d)", d)
    code = f"D{day.group(1)}" if day else "D?"
    if "mikoumi" in d or "mikumi" in d:
        code += "K"
    elif "main" in d:
        code += "M"
    pages = re.findall(r"\d+", str(slide or ""))
    return f"{code} p{'-'.join(pages)}" if pages else code


def _year(v):
    """2026, '2026 (to May)', '2026 (to end March)' -> 2026."""
    m = re.search(r"(19|20)\d{2}", str(v or ""))
    return int(m.group(0)) if m else None


def value_type(v) -> str | None:
    """The workbook's "Value type" column, normalised. None means do not load.

    flow = new in the year (years may be added); cumulative = a stock at that
    date (never added across years); active = patients in care at that date;
    point-in-time = one dated count ("as presented (2026 only)" and the
    Zimbabwe district table are dated single counts too); unclear = not
    loaded until confirmed (Malawi)."""
    s = str(v or "").strip().lower()
    if s.startswith("flow"):
        return "flow"
    if s.startswith("cumulative"):
        return "cumulative"
    if s.startswith("active"):
        return "active"
    if s.startswith("point-in-time") or s.startswith("as presented"):
        return "point-in-time"
    return None


LOAD_MAP_CONDITION = {
    "t1d": "t1d", "scd": "scd", "rhd": "rhd",
    "cardiac, not split": "cardiac_not_split",
    "sentinel, not split": "sentinel_not_split",
}


def from_icppa(path, skipped=None):
    """Return {(country, year): record} rebuilt from the ICPPA 2026 extraction (v2).

    Reading rules (workbook README, "Value type"):
      - flow rows with Include = Y are new enrolments in that year; ever
        enrolled is their running sum;
      - cumulative and active rows are stocks: each loads as its own year's
        value and is never added to another year. They load whatever their
        Include flag, because the flag only stops the workbook's own summary
        from adding years (Kenya's earlier cumulative rows, Rwanda's series);
      - point-in-time rows with Include = Y are one dated count;
      - unclear rows are not loaded (Malawi enrolment, Q-MWI-01).
    Severe hypertension and the non-sentinel columns are kept as their own
    conditions and never enter a sentinel total (common.TRACERS).
    Every value keeps its deck and slide (fact_value_source).

    `skipped`, if given, collects (country, sheet, reason) for the run log.
    """
    skipped = skipped if skipped is not None else []
    wb = openpyxl.load_workbook(path, data_only=True)
    # (country, year) -> {"flow": {cond: n}, "stock": {cond: n}, "active": {cond: n},
    #                     "types": set, "refs": {cond: set}, "ctx": {...}}
    cells = defaultdict(lambda: {"flow": defaultdict(int), "stock": defaultdict(int),
                                 "active": defaultdict(int), "types": set(),
                                 "refs": defaultdict(set), "ctx": {}, "ctx_refs": {},
                                 "as_of": None})

    for r in _rows(wb["Enrolment_by_Year"]):
        country, year = r.get("Country"), _year(r.get("Year"))
        if not country or not year:
            continue
        vt = value_type(r.get("Value type"))
        include = str(r.get("Include in country total", "")).strip().upper() == "Y"
        if vt is None:
            skipped.append((country, "Enrolment_by_Year",
                            f"{year}: value type '{r.get('Value type')}' not loaded"))
            continue
        if vt in ("flow", "point-in-time") and not include:
            skipped.append((country, "Enrolment_by_Year", f"{year}: Include = N"))
            continue
        bucket = {"flow": "flow", "point-in-time": "stock", "cumulative": "stock",
                  "active": "active"}[vt]
        ref = source_ref(r.get("Source document"), r.get("Slide no."))
        c = cells[(country, year)]
        c["types"].add(vt)
        for col, key in ICPPA_CONDITION_MAP.items():
            v = _int(r.get(col))
            if v is not None:
                c[bucket][key] += v
                c["refs"][key].add(ref)

    for r in _rows(wb["Staff_Trained_by_Year"]):
        country, year = r.get("Country"), _year(r.get("Year"))
        if not country or not year:
            continue
        if str(r.get("Include in country total", "")).strip().upper() != "Y":
            skipped.append((country, "Staff_Trained_by_Year", f"{year}: Include = N"))
            continue
        # The cadre cells, not the printed total: where the two disagree the
        # cells are what the workbook transcribed (Liberia 407 not 490,
        # Q-LBR-04; Sierra Leone PIH 2025 13 not 11, Q-SLE-02).
        total = _sum_present(_int(r.get(col)) for col in ICPPA_CADRE_MAP)
        if total is None:
            continue
        vt = value_type(r.get("Value type")) or "flow"
        key = "trained_hist" if vt == "flow" else "trained_hist_cumulative"
        c = cells[(country, year)]
        c["ctx"][key] = c["ctx"].get(key, 0) + total
        c["ctx_refs"].setdefault(key, set()).add(source_ref(r.get("Source document"), r.get("Slide no.")))

    if "Load_Map_Other_Figures" in wb.sheetnames:
        for r in _rows(wb["Load_Map_Other_Figures"]):
            country = r.get("Country")
            if not country:
                continue
            if str(r.get("Load?", "")).strip().upper() != "Y":
                continue
            v, vt = _int(r.get("Value")), value_type(r.get("Value type"))
            as_of = r.get("As of")
            year = _year(as_of)
            if v is None or vt is None or not year:
                skipped.append((country, "Load_Map_Other_Figures",
                                f"{r.get('Load as')}: no usable value / type / date"))
                continue
            ref = source_ref(r.get("Source document"), r.get("Slide no."))
            c = cells[(country, year)]
            c["types"].add(vt)
            as_of = as_of.date().isoformat() if hasattr(as_of, "date") else str(as_of)[:10]
            c["as_of"] = max(filter(None, [c["as_of"], as_of]))
            ind = str(r.get("Indicator") or "").strip()
            cond = str(r.get("Condition") or "").strip().lower()
            load_as = str(r.get("Load as") or "").lower()
            if ind == "2.5":
                c["ctx"]["patients_all_ever"] = v
                c["ctx_refs"]["patients_all_ever"] = {ref}
            elif ind == "2.6" and "active" in load_as and cond == "all":
                # Zambia: active in care across ALL PEN-Plus conditions. Not a
                # sentinel figure, so it is published with 2.5, not 2.6a.
                c["ctx"]["patients_all_active"] = v
                c["ctx_refs"]["patients_all_active"] = {ref}
            elif ind == "2.6" and cond in LOAD_MAP_CONDITION:
                key = LOAD_MAP_CONDITION[cond]
                bucket = "active" if "active" in load_as else "stock"
                c[bucket][key] += v
                c["refs"][key].add(ref)
            elif ind == "3.3":
                key = "trained_hist" if vt == "flow" else "trained_hist_cumulative"
                c["ctx"][key] = c["ctx"].get(key, 0) + v
                c["ctx_refs"].setdefault(key, set()).add(ref)
            else:
                skipped.append((country, "Load_Map_Other_Figures",
                                f"{r.get('Load as')} / {cond}: no mapping"))

    sites = {}
    for r in _rows(wb["Sites_and_Clinics"]):
        country = r.get("Country")
        if country:
            m = re.match(r"\s*(\d+)", str(r.get("Number of PEN-Plus sites / clinics") or ""))
            sites[country] = int(m.group(1)) if m else None

    out = {}
    for country in sorted({c for c, _ in cells} | set(sites)):
        if country not in COUNTRIES:
            skipped.append((country, "all sheets", "country not in the Phase Two list"))
            continue
        years = sorted(y for c, y in cells if c == country) or [2026]
        running = defaultdict(int)
        seen = set()
        trained_to_date = None
        for year in years:
            c = cells[(country, year)]
            for k, v in c["flow"].items():
                running[k] += v
                seen.add(k)
            ever = {k: running[k] for k in seen}
            ever.update(c["stock"])          # a stock at this date replaces nothing summed
            conds = sorted(set(ever) | set(c["active"]))
            flow_trained = c["ctx"].get("trained_hist")
            if flow_trained is not None:
                trained_to_date = (trained_to_date or 0) + flow_trained
            if c["ctx"].get("trained_hist_cumulative") is not None:
                trained_to_date = c["ctx"]["trained_hist_cumulative"]

            closing = c["as_of"] or _closing_date_for_year(year)
            closing = min(closing, dt.date.today().isoformat())
            rec = {
                "country_name": country,
                "rhythm": "annual", "period_id": f"{year}-A",
                "quarter_id": f"{year}-Q4", "year": year,
                "closing_date": closing,
                "source_file": os.path.basename(path),
                "form_version": "icppa_2026",
                "patient_stock": [
                    {"condition": k, "ever_enrolled": ever.get(k),
                     "active_end": c["active"].get(k)} for k in conds],
                "patient_flow": [
                    {"condition": k, "new_enrolled": v, "ltfu": None,
                     "transferred_out": None, "stopped": None, "died": None}
                    for k, v in c["flow"].items()],
                "workforce": [], "governance": [],
                "context": {}, "quality": {}, "confidence": {},
                "facilities": [], "facility_period": [],
                "value_sources": [],
            }
            for key in ("patients_all_ever", "patients_all_active"):
                if key in c["ctx"]:
                    rec["context"][key] = c["ctx"][key]
            if flow_trained is not None:
                rec["context"]["trained_hist"] = flow_trained
            if trained_to_date is not None:
                rec["context"]["trained_hist_to_date"] = trained_to_date
            if year == years[-1] and sites.get(country) is not None:
                rec["context"]["sites_reported_icppa"] = sites[country]

            # provenance: one row per published (indicator, disaggregation)
            vtype = "/".join(sorted(c["types"])) or None
            sentinel_refs = set().union(*(c["refs"][k] for k in conds if k in SENTINEL_SUM)) \
                if any(k in SENTINEL_SUM for k in conds) else set()
            if any(k in SENTINEL_SUM for k in ever):
                rec["value_sources"].append(_vs("2.6", "all", vtype, sentinel_refs))
            if any(k in SENTINEL_SUM for k in c["active"]):
                rec["value_sources"].append(_vs("2.6a", "all", "active", sentinel_refs))
            for k in conds:
                rec["value_sources"].append(_vs("2.6" if k in SENTINEL_SUM else "2.5", k,
                                                vtype, c["refs"][k]))
                if k in c["active"]:
                    rec["value_sources"].append(_vs("2.6a", k, "active", c["refs"][k]))
            if "patients_all_ever" in c["ctx"]:
                rec["value_sources"].append(_vs("2.5", "all", "cumulative",
                                                c["ctx_refs"]["patients_all_ever"]))
            if "patients_all_active" in c["ctx"]:
                rec["value_sources"].append(_vs("2.5", "active", "active",
                                                c["ctx_refs"]["patients_all_active"]))
            trained_refs = set().union(*(c["ctx_refs"].get(k, set())
                                         for k in ("trained_hist", "trained_hist_cumulative")))
            if trained_refs:
                rec["value_sources"].append(_vs("3.3", "all", "flow", trained_refs))
                rec["value_sources"].append(_vs("3.3", "to_date", "cumulative", trained_refs))
            out[(country, year)] = rec
    return out


def _vs(code, disagg, vtype, refs):
    return {"indicator_code": code, "disagg_value": disagg, "value_type": vtype,
            "source_ref": "; ".join(sorted(r for r in refs if r)) or None}


def _sum_present(values):
    vals = [v for v in values if v is not None]
    return sum(vals) if vals else None


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


def norm_status(v):
    return STATUS_MAP.get(str(v).strip().lower(), "not_reported") if v else "not_reported"


def from_monitoring(path):
    """Governance milestones and district counts from the phase 1 workbook.

    The sheets are hand-built, with banner rows above the real header and country
    names in a column that is not the first. The reader therefore looks for the
    header row rather than assuming row 1.
    """
    wb = openpyxl.load_workbook(path, data_only=True)
    out = {}

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
        for row in ws.iter_rows(min_row=hrow, max_row=hrow + 2, values_only=True):
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


# Every step's own wording begins "Step N." in
# Phase_1_PEN-Plus_Reporting_Tools.docx (section 3); a real workbook column
# header derived from that form is expected to keep the step number even if
# the rest of the wording is paraphrased or truncated, so matching on
# "Step <n>" is far more robust than matching the full description text.
_STEP_NO_RE = re.compile(r"step\s*0*(\d{1,2})\b", re.I)


def _match_step_no(header_text: str) -> int | None:
    m = _STEP_NO_RE.search(header_text)
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= len(IMPLEMENTATION_STEPS) else None
    # Fall back to matching a distinctive fragment of the step's own wording,
    # for a header that dropped the "Step N" prefix entirely.
    low = header_text.lower()
    for step_no, _, _, step_label in IMPLEMENTATION_STEPS:
        frag = step_label.lower()[:30]
        if frag and frag in low:
            return step_no
    return None


def from_monitoring_phases(path):
    """Per-country implementation-phase status from the round 1 monitoring
    workbook's PEN-Plus-phases sheet.

    Headers span two rows (a step's number and its description are often on
    separate lines in a hand-built sheet); the country column is found by its
    header (column C in the real workbook).
    Columns are mapped to a step by the header text, never by position --
    some rows in this workbook carry extra cells, which would otherwise
    shift every later column out of alignment.

    Returns {iso3: {step_no: status}}.
    """
    wb = openpyxl.load_workbook(path, data_only=True)
    sheet_name = next((n for n in wb.sheetnames if "phase" in n.lower()), None)
    if sheet_name is None:
        return {}
    ws = wb[sheet_name]

    HEADER_ROWS = (7, 8)

    top = next(ws.iter_rows(min_row=HEADER_ROWS[0], max_row=HEADER_ROWS[0], values_only=True), ())
    bottom = next(ws.iter_rows(min_row=HEADER_ROWS[1], max_row=HEADER_ROWS[1], values_only=True), ())
    width = max(len(top), len(bottom))
    # The country column is whichever header cell reads "Country"/"Countries".
    # It used to be hard-coded as index 3; the real sheet has it in column C
    # (index 2), so the reader matched 0 of 20 countries and the site showed
    # all 31 as "not started" (audit v2, section 1). Index 2 is the fallback.
    COUNTRY_COL = next(
        (j for j in range(width)
         for v in ((top[j] if j < len(top) else None), (bottom[j] if j < len(bottom) else None))
         if v and str(v).strip().lower().startswith("countr")),
        2)
    col_to_step: dict[int, int] = {}
    for j in range(width):
        label = " ".join(
            str(v).strip() for v in (top[j] if j < len(top) else None, bottom[j] if j < len(bottom) else None)
            if v
        )
        if not label:
            continue
        step_no = _match_step_no(label)
        if step_no:
            col_to_step[j] = step_no

    out: dict[str, dict[int, str]] = {}
    for row in ws.iter_rows(min_row=max(HEADER_ROWS) + 1, values_only=True):
        if COUNTRY_COL >= len(row):
            continue
        country = str(row[COUNTRY_COL] or "").strip()
        if country not in COUNTRIES:
            continue
        iso3 = COUNTRIES[country][0]
        steps = {step_no: norm_status(row[j]) for j, step_no in col_to_step.items() if j < len(row)}
        if steps:
            out[iso3] = steps
    return out


def _blank_monitoring_rec(country, path):
    return {"country_name": country, "rhythm": "annual", "period_id": "2025-A",
            "quarter_id": "2025-Q4", "year": 2025,
            "closing_date": _closing_date_for_year(2025),
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
        for _country, rec in sorted(from_monitoring(args.monitoring).items()):
            load_return(con, rec, source_kind="historical", provenance=PROV_MON)
            n += 1

    for (_country, _year), rec in sorted(from_icppa(args.icppa).items()):
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
