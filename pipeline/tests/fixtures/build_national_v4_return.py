"""
build_national_v4_return.py - fills the REAL new national quarterly tool with
SYNTHETIC figures, for testing parse.py and validate.py only.

Not a real country return: every figure below is invented. The template is
docs/refinement/03_reporting_form/PEN-Plus_2_National_Level_Quarterly_Reporting_Tool_NEW.docx,
filled cell by cell so the test exercises the tool's own table layout rather
than an imitation of it. Rows are found by their label, as parse.py finds them.
"""
from __future__ import annotations

import copy
import os

from docx import Document

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "..", "..", "docs", "refinement", "03_reporting_form",
                        "PEN-Plus_2_National_Level_Quarterly_Reporting_Tool_NEW.docx")

#: The default synthetic figures. Arithmetic is consistent, so every
#: validation rule passes on them; a test breaks one on purpose.
DEFAULT = {
    "ident": {"Country": "Ghana", "Reporting quarter": "Q3", "Year": "2026",
              "Period covered": "2026-07-01 to 2026-09-30", "Date completed": "2026-10-20"},
    "context": {"Health districts in the country": 261,
                "First-referral / district hospitals": 100,
                "Health districts where PEN-Plus": 5,
                "PEN-Plus facilities expected": 5,
                "Facilities submitting a complete": 4,
                "Facilities submitting a partial": 1,
                "Facilities submitting no return": 0},
    "governance": {"1.1": ("Yes", "2024", "National NCD Strategy 2024-2028"),
                   "1.2": ("Under development", "", ""),
                   "1.3": ("No", "", "")},
    "guidelines": {"Type 1 diabetes": ("Yes", "Yes", "T1D protocol, 2025"),
                   "Sickle cell disease": ("Yes", "No", "SCD protocol, 2025"),
                   "Rheumatic heart disease": ("No", "No", "")},
    "fac_23": {"Facilities that have initiated": 5, "Of these, facilities active": 5},
    "quality_24": {"Facilities assessed with": 3, "Facilities meeting criteria": 2,
                   "Proportion achieving": 67},
    "all_25": (900, 60),
    # condition: (ever, new, active, retention % as printed -- never read)
    "sentinel_26": {"Type 1 diabetes": (300, 20, 280, 350),
                    "Sickle cell disease": (400, 30, 370, 0),
                    "Rheumatic heart disease": (100, 5, 90, 0)},
    "academy_31": (4, 3, 0, 7),
    "trained_33": {"Medical doctors / specialists": (1, 2, 3, 10),
                   "Nurses / midwives": (5, 1, 6, 15)},
    "mentorship_34": (4, 5, 80),
    "round_table": ("Yes", "Round table, 12 August 2026"),
    "hmis_52": ("Yes", 12),
    "comm_61_total": 3,
    "consent": "Yes",
    # five Active facilities in Annex A, matching 2.3 "active during period" (R02)
    "facilities": [(f"GHA-000{i}", f"Synthetic Hospital {c}", "Region A", f"District {c}",
                    "District", "2023", "Active", "Yes", "T1D; SCD; RHD")
                   for i, c in enumerate("ABCDE", start=1)],
}


def _set(cell, value):
    cell.text = "" if value is None else str(value)


def _row(table, label):
    for row in table.rows:
        if row.cells[0].text.strip().lower().startswith(label.lower()):
            return row
    raise KeyError(f"row '{label}' not found in table starting '{table.rows[0].cells[0].text[:30]}'")


def _table(doc, header_start):
    for t in doc.tables:
        if t.rows and t.rows[0].cells[0].text.strip().lower().startswith(header_start.lower()):
            return t
    raise KeyError(header_start)


def _tables(doc, header_start):
    return [t for t in doc.tables
            if t.rows and t.rows[0].cells[0].text.strip().lower().startswith(header_start.lower())]


def build_national_v4_return(path: str, **overrides) -> dict:
    """Write a filled copy of the new tool to `path`; returns the figures used."""
    data = copy.deepcopy(DEFAULT)
    data.update(overrides)
    doc = Document(TEMPLATE)

    ident = _table(doc, "Field")
    for label, value in data["ident"].items():
        _set(_row(ident, label).cells[1], value)
    ctx = _table(doc, "Item")
    for label, value in data["context"].items():
        _set(_row(ctx, label).cells[1], value)

    gov = _table(doc, "Code")
    for code, (status, year, doc_title) in data["governance"].items():
        r = _row(gov, code)
        _set(r.cells[2], status)
        _set(r.cells[3], year)
        _set(r.cells[4], doc_title)

    gl = _table(doc, "Condition")
    for label, (validated, dissem, title) in data["guidelines"].items():
        r = _row(gl, label)
        _set(r.cells[1], validated)
        _set(r.cells[2], dissem)
        _set(r.cells[3], title)

    measure_tables = _tables(doc, "Measure")      # 2.2, 2.3, 2.4, 3.1, 3.4 in order
    t23 = next(t for t in measure_tables if "initiated" in t.rows[1].cells[0].text.lower())
    for label, value in data["fac_23"].items():
        _set(_row(t23, label).cells[1], value)
    t24 = next(t for t in measure_tables if "quality checklist" in t.rows[1].cells[0].text.lower())
    for label, value in data["quality_24"].items():
        _set(_row(t24, label).cells[1], value)

    t25 = _table(doc, "PEN-Plus condition")
    ever, new = data["all_25"]
    _set(t25.rows[1].cells[1], ever)
    _set(t25.rows[1].cells[2], new)

    t26 = _table(doc, "Priority / sentinel")
    for label, (e, n, a, pct) in data["sentinel_26"].items():
        r = _row(t26, label)
        for j, v in enumerate((e, n, a, pct), start=1):
            _set(r.cells[j], v)

    t31 = next(t for t in measure_tables if "academy" in t.rows[1].cells[0].text.lower())
    for j, v in enumerate(data["academy_31"], start=1):
        _set(t31.rows[1].cells[j], v)

    t33 = next(t for t in _tables(doc, "Cadre") if "this quarter" in t.rows[0].cells[1].text.lower())
    for label, vals in data["trained_33"].items():
        r = _row(t33, label)
        for j, v in enumerate(vals, start=1):
            _set(r.cells[j], v)

    t34 = next(t for t in measure_tables if "mentorship" in t.rows[1].cells[0].text.lower())
    num, den, pct = data["mentorship_34"]
    _set(_row(t34, "Facilities receiving").cells[1], num)
    _set(_row(t34, "Total facilities providing").cells[1], den)
    _set(_row(t34, "Proportion with").cells[1], pct)

    rt = next(t for t in _tables(doc, "Item") if "meeting" in t.rows[1].cells[0].text.lower())
    _set(rt.rows[1].cells[1], data["round_table"][0])
    _set(rt.rows[1].cells[2], data["round_table"][1])

    hm = next(t for t in _tables(doc, "Item") if "hmis" in t.rows[1].cells[0].text.lower()
              or "integrated" in t.rows[1].cells[0].text.lower())
    _set(_row(hm, "PEN-Plus indicators integrated").cells[1], data["hmis_52"][0])
    _set(_row(hm, "Number of PEN-Plus indicators").cells[1], data["hmis_52"][1])

    comm = _table(doc, "Product type")
    _set(_row(comm, "TOTAL").cells[1], data["comm_61_total"])
    consent = _table(doc, "Safeguard")
    _set(consent.rows[1].cells[1], data["consent"])

    annex = _table(doc, "Facility ID")
    for i, fac in enumerate(data["facilities"], start=1):
        for j, v in enumerate(fac):
            _set(annex.rows[i].cells[j], v)

    doc.save(path)
    return data
