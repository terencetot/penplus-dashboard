"""
build_synthetic_return.py - generates a SYNTHETIC .docx fixture for testing parse.py only.

This is not a real WHO AFRO country return. Every name, figure and identifier
below is invented for the test suite. It exists so test_parse.py can exercise
index_tables()/rows_of()/by_label() against a structurally faithful document
without checking a binary .docx into the repository. Do not copy this data
into seed_history.py or anywhere a real return is expected.

Layout mirrors what parse.py's index_tables() looks for: numbered section
paragraphs ("1.", "2.1", "3.", "6.1") or Annex/Block paragraphs, each
immediately followed by the table(s) that belong to it.
"""
from __future__ import annotations

from docx import Document


def _add_table(doc, rows):
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            table.cell(i, j).text = str(val)
    return table


def build_synthetic_return(path: str, broken: bool = False) -> None:
    """Write a synthetic PEN-Plus return .docx to `path`.

    broken=True omits Section 1 entirely, to exercise parse_return()'s
    "reject a structurally altered return" ValueError.
    """
    doc = Document()

    if not broken:
        doc.add_paragraph("1. Identification")
        _add_table(doc, [
            ["Field", "Value"],
            ["Country name", "Ghana"],
            ["Reporting rhythm", "Quarterly"],
            ["Period reported", "Quarter 1"],
            ["Year", "2026"],
            ["Closing date of the count", "2026-03-31"],
            ["Number of days in this reporting period", "90"],
            ["M&E officer name", "Jane Doe"],
            ["NCD national professional officer (NPO)", "John Smith"],
            ["National PEN-Plus focal point", "Focal Person"],
            ["Email", "test@example.org"],
            ["Is this the country's first return?", "No"],
        ])
    else:
        # A deliberately broken document: no Section 1 heading anywhere.
        doc.add_paragraph("Some unrelated cover note")

    doc.add_paragraph("2.1 Patient stock at period end")
    _add_table(doc, [
        ["Condition", "Ever enrolled", "Active at period end"],
        ["Type 1 diabetes", "150", "140"],
        ["Sickle cell disease", "NR", "60"],               # NR -> None
        ["Rheumatic heart disease", "45", "-"],            # blank dash -> None
        ["Severe hypertension", "Not reported", "190"],    # "not reported" -> None
        ["Total", "640", "640"],
    ])

    doc.add_paragraph("2.2 Patient flow during the period")
    _add_table(doc, [
        ["Condition", "New enrolled", "LTFU", "Transferred out", "Stopped", "Died"],
        ["Type 1 diabetes", "20", "3", "1", "0", "2"],
        ["Sickle cell disease", "10", "1", "0", "0", "1"],
        ["Rheumatic heart disease", "5", "0", "0", "0", "0"],
        ["Severe hypertension", "25", "4", "2", "1", "3"],
    ])

    doc.add_paragraph("3. Health workforce")
    _add_table(doc, [
        ["Cadre", "Trained F", "Trained M", "Fully trained", "Working at site"],
        ["Medical doctors and specialists", "3", "4", "12", "10"],
        ["Clinical officers or clinical associates", "2", "2", "8", "7"],
        ["Nurses and midwives", "6", "3", "25", "22"],
        ["Pharmacy and laboratory staff", "1", "1", "4", "4"],
        ["Other cadres", "0", "1", "2", "2"],
        ["Total", "12", "11", "51", "45"],
    ])

    doc.add_paragraph("6.1 Governance milestones")
    _add_table(doc, [
        ["Milestone", "Status", "Achieved in", "Document"],
        ["National PEN-Plus strategy adopted", "Yes", "2024", "strategy.pdf"],
        ["Costed implementation plan", "Under development", "-", "-"],
    ])

    doc.add_paragraph("Annex A: Facility register")
    doc.add_paragraph("Block 1: Facility identity")
    _add_table(doc, [
        ["Facility ID", "Name", "District", "Region", "Facility type",
         "Services started", "Conditions", "Project supported", "Status"],
        ["GHA-0001", "Korle Bu Teaching Hospital", "Accra Metro", "Greater Accra",
         "Tertiary", "2023-01", "t1d,scd,rhd,severe_htn", "Yes", "Operational"],
        ["GHA-0002", "Komfo Anokye Teaching Hospital", "Kumasi", "Ashanti",
         "Tertiary", "2023-06", "t1d,scd", "Partial", "Opened this period"],
    ])

    doc.save(path)
