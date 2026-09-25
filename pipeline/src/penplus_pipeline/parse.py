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
# Current form: a sub-indicator banner's own cell reads "Indicator 2.5", not
# the bare code the previous copy used ("2.5 | ..."). Both are recognised so
# a fixture built against either copy still parses.
INDICATOR_RE = re.compile(r"^indicator\s+(\d+(?:\.\d+)?)\b", re.I)
ANNEX_RE = re.compile(r"^annex\s+([a-f])\b", re.I)
# Annex A now holds a single table, the facility register. "Facility
# register" itself is a one-row banner *table* ahead of it ("Facility
# register | Update only when a facility changes"), not a plain paragraph as
# in the previous copy of the form -- it carries no data of its own and is
# dropped like the "feeds/version/round" banners below, so the register table
# lands under the plain "annex_a" key.
ANNEX_A_REGISTER_RE = re.compile(r"^facility register", re.I)


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
                if INDICATOR_RE.match(head):
                    key = "s" + INDICATOR_RE.match(head).group(1)
                    continue
                if SECTION_RE.match(head):
                    key = "s" + SECTION_RE.match(head).group(1)
                    continue
                if ANNEX_RE.match(head):
                    key = "annex_" + ANNEX_RE.match(head).group(1).lower()
                    continue
                if ANNEX_A_REGISTER_RE.match(head):
                    continue                      # banner only, no data of its own
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
    """Read a completed Phase_2_PEN-Plus_Reporting_Tools.docx return.

    Section numbers below are the form's own (0 identification, 1 governance,
    2 service delivery, 3 workforce, 4 financing, 5 health information, 6
    communication, Annex A facilities) -- not the data model workbook's
    numbering, which the real form does not follow. See docs/architecture.md,
    "Indicator list corrected against the real reporting forms".
    """
    idx = index_tables(path)
    rec = {"source_file": os.path.basename(path),
           "checksum": hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]}

    # ---- Section 0: identification, national context and reporting
    # completeness. The current form merges what used to be two tables
    # (national context, then a separate facility-return-count table) into
    # one "National context and reporting completeness" table -- both halves
    # are read from the same block (index 1) below. "Closing date of the
    # quarter" and "is this the country's first return" no longer exist on
    # this form; "facilities whose return arrived by the national deadline"
    # (returns_on_time) is gone too -- timeliness is now self-reported
    # directly under indicator 5.1 instead (see below).
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
    rec["closing_date"] = clean(pick(ident, "closing date")) or _quarter_end_date(rec["period_id"])
    rec["me_officer"] = clean(pick(ident, "m&e focal point"))
    rec["npo"] = clean(pick(ident, "npo / who country office"))
    rec["focal_point"] = clean(pick(ident, "national programme focal point"))
    rec["first_return"] = enum(pick(ident, "is this the country"), YESNO_KEY)

    ctx = by_label(rows_of(idx, "s0", 1))
    rec["context"] = {
        "districts_total": num(pick(ctx, "health districts in the country")),
        "first_referral_total": num(pick(ctx, "first-referral")),
        "districts_with_penplus": num(pick(ctx, "health districts where pen-plus")),
    }
    rec["quality"] = {
        "facilities_expected": num(pick(ctx, "pen-plus facilities expected")),
        "returns_complete": num(pick(ctx, "facilities submitting a complete")),
        "returns_partial": num(pick(ctx, "facilities submitting a partial")),
        "returns_none": num(pick(ctx, "facilities submitting no return")),
        "returns_on_time": None,
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

    # ---- Sections 2.2, 2.3, 2.4, 3.4: the country-reported aggregate tables
    # in these sections are still not parsed here, on purpose -- Annex A's
    # facility-level detail was always the auditable source for these, and
    # the two were never guaranteed to reconcile line for line (see
    # docs/architecture.md). Annex A no longer carries that facility-level
    # detail on the current form (it moved to the new monthly facility
    # return, not yet wired into this pipeline -- see docs/reporting-form.md),
    # so until that form is read, 2.2, 2.4 and 3.4 have no source to compute
    # from and correctly render as not-yet-reported rather than switching to
    # the country's own aggregate answer, which this pipeline has never
    # trusted as the primary source. 2.3 still resolves from the facility
    # register's own status column (see the fallback a few lines below).

    # ---- Section 2.5: patients ever enrolled, cumulative, and newly
    # enrolled this quarter -- the current form moved "newly enrolled" into
    # this table's own third column; the previous copy carried it only in
    # the optional supplementary block that used to follow 2.6. The
    # deduplication-method question that used to sit beside this table is
    # gone from the current form.
    rec["patient_stock"], rec["patient_flow"], rec["patient_age"] = [], [], []
    flow_by_cond: dict[str, dict] = {}
    for r in rows_of(idx, "s2.5", 0)[1:]:
        c = CONDITION_KEY.get(r[0].strip().lower())
        if c:
            rec["patient_stock"].append(
                {"condition": c, "ever_enrolled": num(r[1]), "active_end": None})
            if c != "total":
                flow_by_cond[c] = {"condition": c, "new_enrolled": num(r[2]) if len(r) > 2 else None,
                                    "ltfu": None, "transferred_out": None, "died": None, "stopped": None}
    rec["dedup_basis"] = None

    # ---- Section 2.6: active in care and twelve-month retention. Three
    # blocks follow this indicator's banner on the current form: the
    # retention table itself: a supplementary patient-movement table
    # (condition x lost-to-follow-up/transferred/stopped/died -- newly
    # enrolled has moved out of this table and up into 2.5, and the column
    # order is not the same as the previous copy's); and the focus area's
    # activity log (not parsed). The "which loss-to-follow-up rule was
    # applied" question the previous copy asked every quarter is gone
    # entirely -- the regional 90-day rule is now the fixed definition
    # rather than a per-return self-attestation, so retention is computed
    # whenever a numerator/denominator is given, without that gate.
    stock_by_cond = {s["condition"]: s for s in rec["patient_stock"]}
    retention_pct_reported = {}
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
        if len(r) > 4 and c != "total":
            retention_pct_reported[c] = num(r[4])
    rec["ltfu_rule"] = None
    rec["ltfu_compliant"] = 1
    rec["retention_pct_reported"] = retention_pct_reported
    rec.setdefault("retention", [])

    for r in rows_of(idx, "s2.6", 1)[1:]:
        label = r[0].strip().lower()
        c = CONDITION_KEY.get(label)
        if not c and "other severe" in label:
            c = "other_reported"
        if not c:
            continue
        entry = flow_by_cond.setdefault(
            c, {"condition": c, "new_enrolled": None, "ltfu": None,
                "transferred_out": None, "died": None, "stopped": None})
        entry["ltfu"] = num(r[1]) if len(r) > 1 else None
        entry["transferred_out"] = num(r[2]) if len(r) > 2 else None
        entry["stopped"] = num(r[3]) if len(r) > 3 else None
        entry["died"] = num(r[4]) if len(r) > 4 else None
    rec["patient_flow"] = list(flow_by_cond.values())

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

    # ---- Section 3.3: health workers trained this quarter, by cadre. Unlike
    # 3.2, this table's fourth column is "Total trained this quarter" (a
    # redundant, country-computed total, not a not-stated count) and a fifth
    # column now gives a year-to-date total the country reports directly,
    # rather than that figure being accumulated by the Regional Office from
    # four quarterly returns.
    rec["workforce"] = []
    for r in rows_of(idx, "s3.3", 0)[1:]:
        c = CADRE_KEY.get(r[0].strip().lower())
        if c and c != "total":
            rec["workforce"].append({
                "cadre": c, "trained_f": num(r[1]), "trained_m": num(r[2]),
                "trained_ns": None, "trained_ytd": num(r[4]) if len(r) > 4 else None,
                "fully_trained": None, "working_at_site": None})

    # ---- Section 4.1: resource mobilization, and tracer medicines/diagnostics.
    # The "PEN-Plus or severe NCD budget line" question the previous copy
    # asked alongside the round table is gone from the current form.
    round_table = rows_of(idx, "s4.1", 0)
    rt = by_label(round_table)
    rec["context"]["round_table_held"] = \
        1 if enum(pick(rt, "annual round table held"), YESNO_KEY) == "yes" else \
        (0 if pick(rt, "annual round table held") else None)

    rec["supply"] = []
    for r in rows_of(idx, "s4.1", 1)[1:]:
        if r[0].strip():
            rec["supply"].append({
                "item": r[0].strip(),
                "availability": enum(r[1], AVAIL_KEY, "not_reported"),
                "facilities_stockout": num(r[2]) if len(r) > 2 else None})

    # ---- Section 5.1: HMIS/DHIS2 integration, reporting completeness and
    # timeliness (now partly self-reported), the new data-quality
    # reconciliation block, and confidence declarations.
    his = by_label(rows_of(idx, "s5.1", 0))
    HIS_KEY = {"not integrated": 0, "partially integrated": 1, "fully integrated": 2}
    rec["context"]["his_integration_level"] = \
        HIS_KEY.get((pick(his, "pen-plus indicators integrated") or "").strip().lower())
    rec["quality"]["reported_completeness_pct"] = num(pick(his, "reporting completeness for this quarter"))
    rec["quality"]["reported_timeliness_pct"] = num(pick(his, "reporting timeliness for this quarter"))

    # New: the country self-attests whether its own figures reconcile across
    # sections, rather than that check being only the Regional Office's own
    # note on receipt as it was on the previous copy of the form. Matched by
    # fragment, not raw-slugged, so the stored key stays short and stable
    # even if the question's wording is tightened later.
    recon_rows = by_label(rows_of(idx, "s5.1", 1))
    rec["reconciliation"] = {
        "annex_a_vs_2_3": clean(pick(recon_rows, "facility counts in annex a")),
        "patients_vs_2_5_2_6": clean(pick(recon_rows, "patient totals reconcile")),
        "mentorship_vs_3_4": clean(pick(recon_rows, "mentorship totals reconcile")),
        "definition_changed": clean(pick(recon_rows, "any change in definitions")),
        "figure_corrected": clean(pick(recon_rows, "any correction to a previously")),
    }

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

    # ---- Annex A: facility register only. The current form dropped the
    # "facility return this quarter" performance columns that used to sit
    # alongside the register (ever enrolled, active in care, mentorship,
    # quality score, critical criteria, readiness class) -- that detail
    # moves to the new, separate monthly facility return instead (see
    # docs/reporting-form.md). `facility_period` stays an empty list here
    # until that form is wired in; nothing downstream treats an empty list
    # as a zero, so 2.2/2.4/3.4 correctly render as not-yet-reported rather
    # than fabricating a per-facility figure this form no longer carries.
    rec["facilities"], rec["facility_period"] = [], []
    for r in rows_of(idx, "annex_a", 0)[1:]:
        if not clean(r[0]) and not clean(r[1]):
            continue
        rec["facilities"].append({
            "facility_id": clean(r[0]), "name": clean(r[1]), "region": clean(r[2]),
            "district": clean(r[3]), "facility_type": clean(r[4]),
            "services_started": clean(r[5]), "status": enum(r[6], FSTATUS_KEY),
            "project_supported": enum(r[7], YESNO_KEY) if len(r) > 7 else None,
            "conditions": clean(r[8]) if len(r) > 8 else None})
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


_QUARTER_END = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}


def _quarter_end_date(period_id: str) -> str | None:
    """The calendar closing date of a YYYY-Qn period.

    The current form no longer asks for this directly (the previous copy's
    "closing date of the quarter" field is gone), so it is derived instead --
    every quarter's own end date is common knowledge, not something a country
    should have to type in every return.
    """
    y, _, q = period_id.partition("-Q")
    if q not in _QUARTER_END or not y.isdigit():
        return None
    return f"{y}-{_QUARTER_END[q]}"


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
