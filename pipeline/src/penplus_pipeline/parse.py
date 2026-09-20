#!/usr/bin/env python3
"""
parse.py - read a completed PEN-Plus country report (.docx) into records.

The form is the contract. Tables are located by the heading that precedes them and
rows by their label, never by a hard-coded index, so a table gaining a row does not
break the parser. A structural change that cannot be resolved raises, and the return
is rejected rather than half-read.

    from parse import parse_return
    rec = parse_return("ZMB_2026_Q2_PENPLUS.docx")

NULL discipline: a cell reading NR, "not reported", "-" or empty parses to None.
None is never turned into 0, here or anywhere downstream.
"""
from __future__ import annotations

import hashlib
import os
import re
from collections import OrderedDict

from docx import Document
from docx.oxml.ns import qn

W_T = qn("w:t")
BLANK = {"", "-", "n/a", "na", "choose", "select", "none"}
NOT_REPORTED = {"nr", "not reported", "not available", "unknown", "not assessed"}

CONDITION_KEY = {
    "type 1 diabetes": "t1d",
    "sickle cell disease": "scd",
    "rheumatic heart disease": "rhd",
    "severe hypertension": "severe_htn",
    "total": "total",
}
CADRE_KEY = {
    "medical doctors and specialists": "doctors",
    "clinical officers or clinical associates": "clinical_officers",
    "nurses and midwives": "nurses_midwives",
    "pharmacy and laboratory staff": "pharmacy_lab",
    "other cadres": "other",
    "total": "total",
}
AGE_KEY = {"under 15": "u15", "15 to 29": "15_29", "30 and over": "30plus", "total": "total"}
AVAIL_KEY = {
    "always available": "always", "sometimes available": "sometimes",
    "never available": "never", "not applicable": "not_applicable",
    "not reported": "not_reported",
}
ASSUM_KEY = {
    "holding": "holding", "under strain": "under_strain",
    "not holding": "not_holding", "not assessed": "not_assessed",
}
YESNO_KEY = {
    "yes": "yes", "no": "no", "under development": "under_development",
    "not applicable": "not_applicable", "not reported": "not_reported",
    "partial": "partial",
}
FSTATUS_KEY = {
    "operational": "operational", "opened this period": "started_this_period",
    "under preparation": "under_preparation", "services suspended": "suspended",
    "closed": "closed",
}
MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


# --------------------------------------------------------------------- helpers
def _text(el) -> str:
    """All text under an element, including drop-down content controls."""
    return "".join(t.text or "" for t in el.iter(W_T))


def cell_text(cell) -> str:
    return re.sub(r"\s+", " ", _text(cell._tc)).strip()


def num(v):
    """Parse a reported value to int, or None for a genuine non-response."""
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in BLANK or s in NOT_REPORTED:
        return None
    s = re.sub(r"(usd|\$|over|>|<|~|approx\.?|about|\+)", "", s)
    s = s.replace(",", "").replace(" ", "").replace("%", "")
    try:
        return int(round(float(s)))
    except ValueError:
        return None


def enum(v, table, default=None):
    if v is None:
        return default
    return table.get(str(v).strip().lower(), default)


def clean(v):
    s = (v or "").strip()
    return None if s.lower() in BLANK else s


SECTION_RE = re.compile(r"^(\d+(?:\.\d+)?)[.\s]")
ANNEX_RE = re.compile(r"^annex\s+([a-f])\b", re.I)
BLOCK_RE = re.compile(r"^block\s+(\d)", re.I)


def _blocks(doc):
    """Yield ('p', text) and ('tbl', Table) in document order."""
    body = doc.element.body
    tables = iter(doc.tables)
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield "p", re.sub(r"\s+", " ", _text(child)).strip()
        elif child.tag == qn("w:tbl"):
            yield "tbl", next(tables)


def index_tables(path):
    """Map a logical key to the list of tables sitting under that heading."""
    doc = Document(path)
    out, key = OrderedDict(), None
    for kind, item in _blocks(doc):
        if kind == "p":
            if not item or len(item) > 110:
                continue
            m = SECTION_RE.match(item)
            a = ANNEX_RE.match(item)
            b = BLOCK_RE.match(item)
            if a:
                key = "annex_" + a.group(1).lower()
            elif b and key and key.startswith("annex_a"):
                key = "annex_a_block" + b.group(1)
            elif m:
                key = "s" + m.group(1)
            elif re.match(r"^(national context|completeness|active patients by age|"
                          r"compliance|quality of the count|patients outside|training capacity|"
                          r"assumptions|identification)", item, re.I):
                key = "h_" + re.sub(r"\W+", "_", item.lower())[:34]
        else:
            rows = [[cell_text(c) for c in r.cells] for r in item.rows]
            # A section banner is itself a one-row table: "2.  Patients | Every return".
            if len(rows) == 1 and len(rows[0]) == 2:
                head = rows[0][0].strip()
                if SECTION_RE.match(head):
                    key = "s" + SECTION_RE.match(head).group(1)
                    continue
                if ANNEX_RE.match(head):
                    key = "annex_" + ANNEX_RE.match(head).group(1).lower()
                    continue
                if head.lower().startswith(("feeds", "version", "round")):
                    continue                      # annotation strip, not data
            if key is None:
                continue
            out.setdefault(key, []).append(rows)
    return out


def rows_of(idx, key, n=0):
    t = idx.get(key)
    if t is None:
        for k in idx:
            if k.startswith(key):
                t = idx[k]
                break
    if not t or len(t) <= n:
        return []
    return t[n]


def by_label(rows, col=1):
    """{lower-cased first cell: value at col} for a two-column block."""
    d = OrderedDict()
    for r in rows[1:] if rows else []:
        if len(r) > col and r[0].strip():
            d[r[0].strip().lower()] = r[col]
    return d


def pick(d, *fragments):
    for frag in fragments:
        for k, v in d.items():
            if k.startswith(frag.lower()[:28]):
                return v
    return None


# ----------------------------------------------------------------- the parser
def parse_return(path: str) -> dict:
    idx = index_tables(path)
    rec = {"source_file": os.path.basename(path),
           "checksum": hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]}

    # ---- Section 1: identification, national context, completeness
    ident = by_label(rows_of(idx, "s1"))
    if not ident:
        raise ValueError("Section 1 not found; the form structure has been altered")
    rec["country_name"] = clean(pick(ident, "country"))
    rhythm = (clean(pick(ident, "reporting rhythm")) or "quarterly").lower()
    period = clean(pick(ident, "period reported")) or ""
    year = clean(pick(ident, "year")) or ""
    rec["rhythm"] = "monthly" if rhythm.startswith("month") else "quarterly"
    rec["period_id"] = _period_id(period, year, rec["rhythm"])
    rec["quarter_id"] = _quarter_id(rec["period_id"])
    rec["year"] = int(year) if year.isdigit() else None
    rec["closing_date"] = clean(pick(ident, "closing date"))
    rec["days_in_period"] = num(pick(ident, "number of days"))
    rec["me_officer"] = clean(pick(ident, "m&e officer"))
    rec["npo"] = clean(pick(ident, "ncd national professional"))
    rec["focal_point"] = clean(pick(ident, "national pen-plus focal"))
    rec["email"] = clean(pick(ident, "email"))
    rec["first_return"] = enum(pick(ident, "is this the country"), YESNO_KEY)

    ctx = by_label(rows_of(idx, "h_national_context"))
    rec["context"] = {
        "districts_total": num(pick(ctx, "health districts in the country")),
        "first_referral_total": num(pick(ctx, "first referral facilities")),
        "phc_total": num(pick(ctx, "primary health care facilities")),
        "districts_with_penplus": num(pick(ctx, "health districts where pen-plus")),
        "districts_trained_no_site": num(pick(ctx, "health districts where staff")),
    }

    comp = by_label(rows_of(idx, "h_completeness"))
    rec["quality"] = {
        "facilities_expected": num(pick(comp, "pen-plus facilities expected")),
        "returns_complete": num(pick(comp, "facilities that submitted a complete")),
        "returns_partial": num(pick(comp, "facilities that submitted a partial")),
        "returns_none": num(pick(comp, "facilities that submitted nothing")),
    }

    # ---- Section 2: patients
    rec["patient_stock"], rec["patient_flow"], rec["patient_age"] = [], [], []
    for r in rows_of(idx, "s2.1")[1:]:
        c = CONDITION_KEY.get(r[0].strip().lower())
        if c:
            rec["patient_stock"].append(
                {"condition": c, "ever_enrolled": num(r[1]), "active_end": num(r[2])})
    for r in rows_of(idx, "s2.2")[1:]:
        c = CONDITION_KEY.get(r[0].strip().lower())
        if c:
            rec["patient_flow"].append({
                "condition": c, "new_enrolled": num(r[1]), "ltfu": num(r[2]),
                "transferred_out": num(r[3]), "stopped": num(r[4]), "died": num(r[5])})
    age_rows = rows_of(idx, "h_active_patients_by_age")
    if age_rows:
        bands = [AGE_KEY.get(h.strip().lower()) for h in age_rows[0][1:]]
        for r in age_rows[1:]:
            label = r[0].strip().lower()
            c = CONDITION_KEY.get(label, "total" if label.startswith("all") else None)
            if not c:
                continue
            for band, v in zip(bands, r[1:]):
                if band:
                    rec["patient_age"].append(
                        {"condition": c, "age_band": band, "patients": num(v)})

    comp_def = by_label(rows_of(idx, "h_compliance"))
    applied = enum(pick(comp_def, "the regional ninety-day rule"), YESNO_KEY)
    rec["ltfu_compliant"] = 1 if applied == "yes" else (0 if applied == "no" else None)
    rec["ltfu_rule"] = clean(pick(comp_def, "if not, which rule"))
    qcount = by_label(rows_of(idx, "h_quality_of_the_count"))
    rec["dedup_basis"] = clean(pick(qcount, "how the count was deduplicated"))
    rec["patient_source"] = clean(pick(qcount, "main source of the patient"))
    outside = by_label(rows_of(idx, "h_patients_outside"))
    rec["patient_stock"].append({
        "condition": "other_reported",
        "ever_enrolled": None,
        "active_end": num(pick(outside, "patients active in a pen-plus clinic"))})
    rec["other_conditions"] = clean(pick(outside, "which conditions"))

    # ---- Section 3: workforce
    rec["workforce"] = []
    for r in rows_of(idx, "s3")[1:]:
        c = CADRE_KEY.get(r[0].strip().lower())
        if c:
            rec["workforce"].append({
                "cadre": c, "trained_f": num(r[1]), "trained_m": num(r[2]),
                "fully_trained": num(r[3]), "working_at_site": num(r[4])})
    cap = by_label(rows_of(idx, "h_training_capacity"))
    rec["training_capacity"] = {
        "tots": num(pick(cap, "providers among the above")),
        "master_trainers": num(pick(cap, "active master trainers")),
        "training_centres": num(pick(cap, "active pen-plus training centres")),
    }

    # ---- Section 4: supply
    rec["supply"] = []
    for r in rows_of(idx, "s4")[1:]:
        if r[0].strip():
            rec["supply"].append({
                "item": r[0].strip(),
                "availability": enum(r[1], AVAIL_KEY, "not_reported"),
                "facilities_stockout": num(r[2])})

    # ---- Section 5: service delivery and assumptions
    rec["service"] = []
    for key, required in (("s5.1", 1), ("s5.2", 0)):
        for r in rows_of(idx, key)[1:]:
            if r[0].strip():
                rec["service"].append(
                    {"measure": r[0].strip(), "required": required, "value": num(r[1])})
    rec["assumptions"] = []
    for r in rows_of(idx, "h_assumptions")[1:]:
        if r[0].strip():
            rec["assumptions"].append({
                "assumption": r[0].strip(),
                "status": enum(r[1], ASSUM_KEY, "not_assessed"),
                "signal": clean(r[2]) if len(r) > 2 else None})

    # ---- Section 6: governance
    rec["governance"] = []
    for r in rows_of(idx, "s6.1")[1:]:
        if r[0].strip():
            rec["governance"].append({
                "milestone_code": _slug(r[0]),
                "milestone": r[0].strip(),
                "status": enum(r[1], YESNO_KEY, "not_reported"),
                "achieved_in": clean(r[2]) if len(r) > 2 else None,
                "document": clean(r[3]) if len(r) > 3 else None})
    rec["retention"] = []
    for r in rows_of(idx, "s6.2")[1:]:
        label = r[0].strip().lower()
        c = CONDITION_KEY.get(label, "total" if label.startswith("all") else None)
        if c:
            rec["retention"].append(
                {"condition": c, "numerator": num(r[1]), "denominator": num(r[2])})

    # ---- Section 7: confidence
    conf = {}
    for r in rows_of(idx, "s7.2")[1:] or rows_of(idx, "s7")[1:]:
        if r[0].strip():
            conf[_slug(r[0])] = clean(r[1])
    rec["confidence"] = conf

    # ---- Annex A: facilities
    rec["facilities"], rec["facility_period"] = [], []
    for r in rows_of(idx, "annex_a_block1")[1:]:
        if not clean(r[0]) and not clean(r[1]):
            continue
        rec["facilities"].append({
            "facility_id": clean(r[0]), "name": clean(r[1]), "district": clean(r[2]),
            "region": clean(r[3]), "facility_type": clean(r[4]),
            "services_started": clean(r[5]), "conditions": clean(r[6]),
            "project_supported": enum(r[7], YESNO_KEY),
            "status": enum(r[8], FSTATUS_KEY) if len(r) > 8 else None})
    for r in rows_of(idx, "annex_a_block2")[1:]:
        if not clean(r[0]) and not clean(r[1]):
            continue
        rec["facility_period"].append({
            "facility_id": clean(r[0]), "name": clean(r[1]),
            "return_received": enum(r[2], YESNO_KEY),
            "ever_enrolled": num(r[3]), "active_end": num(r[4]),
            "months_mentorship": num(r[5]), "quality_score": num(r[6]),
            "critical_met": enum(r[7], YESNO_KEY),
            "readiness_class": (r[8] or "").strip().lower() or None})
    return rec


# ---------------------------------------------------------------- period ids
def _period_id(period: str, year: str, rhythm: str) -> str:
    p = (period or "").strip().lower()
    y = year if year.isdigit() else "0000"
    m = re.search(r"quarter\s*([1-4])", p)
    if m:
        return f"{y}-Q{m.group(1)}"
    if p in MONTHS:
        return f"{y}-{MONTHS.index(p) + 1:02d}"
    return f"{y}-{p[:7] or 'NA'}"


def _quarter_id(period_id: str) -> str:
    if "-Q" in period_id:
        return period_id
    y, _, mm = period_id.partition("-")
    try:
        return f"{y}-Q{(int(mm) - 1) // 3 + 1}"
    except ValueError:
        return period_id


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")[:60]


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(parse_return(sys.argv[1]), indent=1, ensure_ascii=False))
