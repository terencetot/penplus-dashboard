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
    "medical doctors / specialists": "doctors",
    "clinical officers / associates": "clinical_officers",
    "nurses / midwives": "nurses_midwives",
    "pharmacy / laboratory staff": "pharmacy_lab",
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
# Annex A's two tables are introduced by plain paragraphs, not a "Block N"
# label: "Facility register" (identity, slowly changing) and "Facility return
# this quarter" (performance, one row of it created per period).
ANNEX_A_REGISTER_RE = re.compile(r"^facility register", re.I)
ANNEX_A_RETURN_RE = re.compile(r"^facility return", re.I)


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
            if a:
                key = "annex_" + a.group(1).lower()
            elif key and key.startswith("annex_a") and ANNEX_A_REGISTER_RE.match(item):
                key = "annex_a_block1"
            elif key and key.startswith("annex_a") and ANNEX_A_RETURN_RE.match(item):
                key = "annex_a_block2"
            elif m:
                key = "s" + m.group(1)
        else:
            rows = [[cell_text(c) for c in r.cells] for r in item.rows]
            # A top-level section banner is a one-row, two-cell table:
            # "1. Governance and leadership | Focus area 1. Q4". A sub-indicator
            # banner is a one-row, three-cell table with the bare code in its own
            # cell: "2.1 | National guidelines... | Q4, or when status changes".
            # An activity-log or optional-block banner has the same three-cell
            # shape but a BLANK first cell ("| Activities this quarter... |
            # Every quarter") -- that carries no key of its own and is not data,
            # so it is dropped rather than read as a one-row table under the
            # still-current key.
            if len(rows) == 1 and len(rows[0]) in (2, 3):
                head = rows[0][0].strip()
                if not head:
                    continue
                # Checked before SECTION_RE: for a bare code like "2.1", the
                # decimal point itself satisfies SECTION_RE's trailing
                # [.\s], so SECTION_RE backtracks and (wrongly) matches with
                # group(1) == "2" -- the fully-numeric case must be tried
                # first, or every sub-indicator banner truncates to its
                # parent section.
                if re.match(r"^\d+(?:\.\d+)?$", head):
                    key = "s" + head
                    continue
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
    """Read a completed Phase_2_PEN-Plus_Reporting_Tools.docx (v3) return.

    Section numbers below are the form's own (0 identification, 1 governance,
    2 service delivery, 3 workforce, 4 financing, 5 health information, 6
    communication, Annex A facilities) -- not the data model workbook's
    numbering, which the real form does not follow. See docs/architecture.md,
    "Indicator list corrected against the real reporting forms".
    """
    idx = index_tables(path)
    rec = {"source_file": os.path.basename(path),
           "checksum": hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]}

    # ---- Section 0: identification, national context, facility returns
    ident = by_label(rows_of(idx, "s0", 0))
    if not ident:
        raise ValueError("Section 0 not found; the form structure has been altered")
    rec["country_name"] = clean(pick(ident, "country"))
    period = clean(pick(ident, "reporting quarter")) or ""
    year = clean(pick(ident, "year")) or ""
    rec["rhythm"] = "quarterly"
    rec["period_id"] = _period_id(period, year, rec["rhythm"])
    rec["quarter_id"] = _quarter_id(rec["period_id"])
    rec["year"] = int(year) if year.isdigit() else None
    rec["closing_date"] = clean(pick(ident, "closing date"))
    rec["me_officer"] = clean(pick(ident, "m&e focal point"))
    rec["npo"] = clean(pick(ident, "npo / who country office"))
    rec["focal_point"] = clean(pick(ident, "national programme focal point"))
    rec["first_return"] = enum(pick(ident, "is this the country"), YESNO_KEY)

    ctx_rows = rows_of(idx, "s0", 1)
    ctx = by_label(ctx_rows)
    rec["context"] = {
        "districts_total": num(pick(ctx, "health districts in the country")),
        "first_referral_total": num(pick(ctx, "first-referral")),
        "districts_with_penplus": num(pick(ctx, "health districts where pen-plus")),
    }

    comp = by_label(rows_of(idx, "s0", 2))
    rec["quality"] = {
        "facilities_expected": num(pick(comp, "pen-plus facilities expected")),
        "returns_complete": num(pick(comp, "facilities submitting a complete")),
        "returns_partial": num(pick(comp, "facilities submitting a partial")),
        "returns_none": num(pick(comp, "facilities submitting no return")),
        "returns_on_time": num(pick(comp, "facilities whose return arrived")),
    }

    # ---- Section 1: governance -- the fixed codes 1.1, 1.2, 1.3
    rec["governance"] = []
    for r in rows_of(idx, "s1", 0)[1:]:
        code = r[0].strip() if r else ""
        if not code:
            continue
        rec["governance"].append({
            "milestone_code": code,
            "milestone": clean(r[1]) if len(r) > 1 else code,
            "status": enum(r[2], YESNO_KEY, "not_reported") if len(r) > 2 else "not_reported",
            "achieved_in": clean(r[3]) if len(r) > 3 else None,
            "document": clean(r[4]) if len(r) > 4 else None})

    # ---- Section 2.1: guideline dissemination, by tracer condition
    for r in rows_of(idx, "s2.1", 0)[1:]:
        c = CONDITION_KEY.get(r[0].strip().lower())
        if c and c != "total":
            rec["context"][f"guideline_disseminated_{c}"] = \
                1 if enum(r[2], YESNO_KEY) == "yes" else (0 if r[2] else None)

    # ---- Sections 2.2, 2.3, 2.4, 3.4: country-reported aggregates are not
    # parsed here. Annex A's facility-level detail is the auditable source
    # for these, and the two are not always reconcilable line for line; see
    # docs/architecture.md.

    # ---- Section 2.5: patients ever enrolled, cumulative
    rec["patient_stock"], rec["patient_flow"], rec["patient_age"] = [], [], []
    for r in rows_of(idx, "s2.5", 0)[1:]:
        c = CONDITION_KEY.get(r[0].strip().lower())
        if c:
            rec["patient_stock"].append(
                {"condition": c, "ever_enrolled": num(r[1]), "active_end": None})
    dedup = by_label(rows_of(idx, "s2.5", 1))
    rec["dedup_basis"] = clean(pick(dedup, "how was the count deduplicated"))

    # ---- Section 2.6: active in care and twelve-month retention
    stock_by_cond = {s["condition"]: s for s in rec["patient_stock"]}
    for r in rows_of(idx, "s2.6", 0)[1:]:
        c = CONDITION_KEY.get(r[0].strip().lower())
        if not c:
            continue
        active = num(r[1])
        if c in stock_by_cond:
            stock_by_cond[c]["active_end"] = active
        else:
            rec["patient_stock"].append({"condition": c, "ever_enrolled": None, "active_end": active})
        rn, rd = (num(r[2]) if len(r) > 2 else None), (num(r[3]) if len(r) > 3 else None)
        if rn is not None or rd is not None:
            rec.setdefault("retention", []).append(
                {"condition": c, "numerator": rn, "denominator": rd})
    rule = by_label(rows_of(idx, "s2.6", 1))
    applied = clean(pick(rule, "loss to follow-up rule applied"))
    rec["ltfu_rule"] = applied
    rec["ltfu_compliant"] = (1 if applied and "90" in applied
                              else (0 if applied else None))
    rec.setdefault("retention", [])

    # optional per-condition flow detail (n=2: the noise banner before it is
    # dropped by index_tables, so the real table lands at this index)
    for r in rows_of(idx, "s2.6", 2)[1:]:
        label = r[0].strip().lower()
        c = CONDITION_KEY.get(label)
        if not c and "other severe" in label:
            c = "other_reported"
        if c:
            rec["patient_flow"].append({
                "condition": c, "new_enrolled": num(r[1]), "ltfu": num(r[2]),
                "transferred_out": num(r[3]), "died": num(r[4]),
                "stopped": num(r[5]) if len(r) > 5 else None})

    # ---- Section 3.1: WHO Academy course completions, cumulative
    who_academy = rows_of(idx, "s3.1", 0)
    if len(who_academy) > 1:
        r = who_academy[1]
        rec["context"]["who_academy_f"] = num(r[1]) if len(r) > 1 else None
        rec["context"]["who_academy_m"] = num(r[2]) if len(r) > 2 else None
        rec["context"]["who_academy_ns"] = num(r[3]) if len(r) > 3 else None

    # ---- Section 3.2: Trainers of Trainers, cumulative by cadre
    rec["workforce_tot"] = []
    for r in rows_of(idx, "s3.2", 0)[1:]:
        c = CADRE_KEY.get(r[0].strip().lower())
        if c and c != "total":
            rec["workforce_tot"].append({
                "cadre": c, "trained_f": num(r[1]), "trained_m": num(r[2]),
                "trained_ns": num(r[3]) if len(r) > 3 else None})

    # ---- Section 3.3: health workers trained this quarter, by cadre
    rec["workforce"] = []
    for r in rows_of(idx, "s3.3", 0)[1:]:
        c = CADRE_KEY.get(r[0].strip().lower())
        if c and c != "total":
            rec["workforce"].append({
                "cadre": c, "trained_f": num(r[1]), "trained_m": num(r[2]),
                "trained_ns": num(r[3]) if len(r) > 3 else None,
                "fully_trained": None, "working_at_site": None})

    # ---- Section 4.1: resource mobilization, and tracer medicines/diagnostics
    round_table = rows_of(idx, "s4.1", 0)
    rt = by_label(round_table)
    rec["context"]["round_table_held"] = \
        1 if enum(pick(rt, "round table held"), YESNO_KEY) == "yes" else \
        (0 if pick(rt, "round table held") else None)
    rec["context"]["budget_line_exists"] = \
        1 if enum(pick(rt, "a pen-plus or severe ncd line"), YESNO_KEY) == "yes" else \
        (0 if pick(rt, "a pen-plus or severe ncd line") else None)

    rec["supply"] = []
    for r in rows_of(idx, "s4.1", 1)[1:]:
        if r[0].strip():
            rec["supply"].append({
                "item": r[0].strip(),
                "availability": enum(r[1], AVAIL_KEY, "not_reported"),
                "facilities_stockout": num(r[2]) if len(r) > 2 else None})

    # ---- Section 5.1: HMIS integration and confidence declarations
    his = by_label(rows_of(idx, "s5.1", 0))
    HIS_KEY = {"not integrated": 0, "partially integrated": 1, "fully integrated": 2}
    rec["context"]["his_integration_level"] = \
        HIS_KEY.get((pick(his, "extent of integration") or "").strip().lower())

    conf = {}
    for r in rows_of(idx, "s5.1", 2)[1:]:
        if r[0].strip():
            conf[_slug(r[0])] = clean(r[1]) if len(r) > 1 else None
    rec["confidence"] = conf

    # ---- Section 6.1: communication and visibility products
    comm_total = None
    for r in rows_of(idx, "s6.1", 0)[1:]:
        if r[0].strip().lower() == "total":
            comm_total = num(r[1]) if len(r) > 1 else None
    rec["context"]["comm_products_total"] = comm_total
    consent = by_label(rows_of(idx, "s6.1", 1))
    rec["context"]["comm_consent_confirmed"] = \
        1 if enum(pick(consent, "documented informed consent"), YESNO_KEY) == "yes" else \
        (0 if pick(consent, "documented informed consent") else None)

    # ---- Annex A: facility register (identity) and quarterly return (performance)
    rec["facilities"], rec["facility_period"] = [], []
    for r in rows_of(idx, "annex_a_block1", 0)[1:]:
        if not clean(r[0]) and not clean(r[1]):
            continue
        rec["facilities"].append({
            "facility_id": clean(r[0]), "name": clean(r[1]), "region": clean(r[2]),
            "district": clean(r[3]), "facility_type": clean(r[4]),
            "services_started": clean(r[5]), "status": enum(r[6], FSTATUS_KEY),
            "project_supported": enum(r[7], YESNO_KEY) if len(r) > 7 else None,
            "conditions": clean(r[8]) if len(r) > 8 else None})
    for r in rows_of(idx, "annex_a_block2", 0)[1:]:
        if not clean(r[0]) and not clean(r[1]):
            continue
        mentorship = enum(r[5], YESNO_KEY) if len(r) > 5 else None
        rec["facility_period"].append({
            "facility_id": clean(r[0]), "name": clean(r[1]),
            "return_received": enum(r[2], YESNO_KEY),
            "ever_enrolled": num(r[3]), "active_end": num(r[4]),
            "mentorship_visit": 1 if mentorship == "yes" else (0 if mentorship == "no" else None),
            "quality_score": num(r[6]) if len(r) > 6 else None,
            "critical_met": enum(r[7], YESNO_KEY) if len(r) > 7 else None,
            "readiness_class": (r[8] or "").strip().lower() if len(r) > 8 else None})
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
