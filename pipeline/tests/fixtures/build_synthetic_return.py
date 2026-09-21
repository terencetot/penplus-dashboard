"""
build_synthetic_return.py - generates a SYNTHETIC .docx fixture for testing parse.py only.

This is not a real WHO AFRO country return. Every name, figure and identifier
below is invented for the test suite. It exists so test_parse.py can exercise
index_tables()/rows_of()/by_label() against a structurally faithful document
without checking a binary .docx into the repository. Do not copy this data
into seed_history.py or anywhere a real return is expected.

Layout mirrors Phase_2_PEN-Plus_Reporting_Tools.docx (v3), the real form
this build was corrected against (see docs/architecture.md): section banners
are one-row tables ("N. Title | context" for a top-level section, "N.M |
Title | context" for a sub-indicator), Annex A's two tables are introduced
by plain paragraphs ("Facility register", "Facility return this quarter"),
not a "Block N" label.
"""
from __future__ import annotations

from docx import Document


def _add_banner(doc, *cells):
    """A one-row banner table: 2 cells for a section, 3 for a sub-indicator."""
    table = doc.add_table(rows=1, cols=len(cells))
    for j, val in enumerate(cells):
        table.cell(0, j).text = val


def _add_table(doc, rows):
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            table.cell(i, j).text = str(val)
    return table


def build_synthetic_return(path: str, broken: bool = False) -> None:
    """Write a synthetic PEN-Plus v3 return .docx to `path`.

    broken=True omits Section 0 entirely, to exercise parse_return()'s
    "reject a structurally altered return" ValueError.
    """
    doc = Document()

    if not broken:
        _add_banner(doc, "0. Identification and reporting completeness", "Every quarter")
        _add_table(doc, [
            ["Field", "Entry"],
            ["Country", "Ghana"],
            ["Reporting quarter", "Quarter 1"],
            ["Year", "2026"],
            ["Closing date of the quarter", "2026-03-31"],
            ["NPO / WHO Country Office focal point", "Jane Doe"],
            ["National programme focal point", "John Smith"],
            ["M&E focal point", "Focal Person"],
            ["Date completed", "2026-04-10"],
            ["Is this the country's first return on this template?", "No"],
        ])
        _add_table(doc, [
            ["National context", "Count"],
            ["Health districts in the country", "20"],
            ["First-referral / district hospitals in the country", "15"],
            ["Health districts where PEN-Plus services are offered", "10"],
        ])
        _add_table(doc, [
            ["Facility returns this quarter", "Count"],
            ["PEN-Plus facilities expected to report this quarter", "10"],
            ["Facilities submitting a complete return", "8"],
            ["Facilities submitting a partial return", "1"],
            ["Facilities submitting no return", "1"],
            ["Facilities whose return arrived by the national deadline", "7"],
        ])
    else:
        # A deliberately broken document: no Section 0 heading anywhere.
        doc.add_paragraph("Some unrelated cover note")

    _add_banner(doc, "1. Governance and leadership", "Focus area 1. Q4")
    _add_table(doc, [
        ["Code", "Results Framework indicator", "Status", "Year achieved", "Document / evidence"],
        ["1.1", "PEN-Plus integrated into the national NCD strategy and UHC agenda",
         "Yes", "2024", "strategy.pdf"],
        ["1.2", "Integrated or stand-alone PEN-Plus Plan developed, approved, launched",
         "Under development", "-", "-"],
        ["1.3", "Costed National Operational Plan (NOP) on PEN-Plus developed and launched",
         "No", "-", "-"],
    ])

    _add_banner(doc, "2. Service delivery and disease management", "Focus area 2")
    _add_banner(doc, "2.1", "National guidelines / protocols adapted, validated and disseminated",
                "Q4, or when status changes")
    _add_table(doc, [
        ["Condition", "Adapted and validated", "Disseminated to all PEN-Plus sites", "Year",
         "Document title"],
        ["Type 1 diabetes", "Yes", "Yes", "2025", "t1d_protocol.pdf"],
        ["Sickle cell disease", "Yes", "No", "2025", "scd_protocol.pdf"],
        ["Rheumatic heart disease", "No", "No", "-", "-"],
        ["Severe hypertension", "Yes", "Yes", "2025", "htn_protocol.pdf"],
        ["Other PEN-Plus condition (specify)", "-", "-", "-", "-"],
    ])

    _add_banner(doc, "2.5", "Unique patients ever enrolled, four tracer conditions",
                "Every quarter")
    _add_table(doc, [
        ["Tracer condition", "Ever enrolled, cumulative"],
        ["Type 1 diabetes", "150"],
        ["Sickle cell disease", "NR"],                 # NR -> None
        ["Rheumatic heart disease", "45"],
        ["Severe hypertension", "Not reported"],       # "not reported" -> None
        ["TOTAL, four tracer conditions", "195"],
    ])
    _add_table(doc, [
        ["Item", "Response"],
        ["How was the count deduplicated?", "Facility register"],
    ])

    _add_banner(doc, "2.6", "Patients active in care, and twelve-month retention",
                "Active: every quarter. Retention: Q4")
    _add_table(doc, [
        ["Tracer condition", "Active in care at end of quarter", "Retention numerator (Q4)",
         "Retention denominator (Q4)"],
        ["Type 1 diabetes", "140", "80", "100"],
        ["Sickle cell disease", "60", "-", "-"],
        ["Rheumatic heart disease", "-", "-", "-"],
        ["Severe hypertension", "190", "-", "-"],
        ["TOTAL, four tracer conditions", "390", "80", "100"],
    ])
    _add_table(doc, [
        ["Item", "Response"],
        ["Loss to follow-up rule applied to the retention figures", "Regional 90-day rule"],
    ])
    _add_banner(doc, "", "Optional: patient detail, only where your system produces it", "Optional")
    _add_table(doc, [
        ["Condition", "Newly enrolled this quarter", "Lost to follow-up", "Transferred out",
         "Died", "Stopped treatment"],
        ["Type 1 diabetes", "20", "3", "1", "2", "0"],
        ["Sickle cell disease", "10", "1", "0", "1", "0"],
        ["Rheumatic heart disease", "5", "0", "0", "0", "0"],
        ["Severe hypertension", "25", "4", "2", "3", "1"],
        ["Patients with other severe NCDs managed in PEN-Plus clinics", "-", "-", "-", "-", "-"],
    ])

    _add_banner(doc, "3. Capacity building and workforce development", "Focus area 3")
    _add_banner(doc, "3.1", "People completing a PEN-Plus WHO Academy course",
                "Pre-filled by WHO AFRO")
    _add_table(doc, [
        ["Measure", "Female", "Male", "Not stated"],
        ["People completing a PEN-Plus WHO Academy course, cumulative", "6", "4", "0"],
    ])

    _add_banner(doc, "3.2", "Health workers trained as Trainers of Trainers", "Every quarter")
    _add_table(doc, [
        ["Cadre", "Female, cumulative", "Male, cumulative", "Not stated"],
        ["Medical doctors / specialists", "2", "3", "0"],
        ["Clinical officers / associates", "1", "1", "0"],
        ["Nurses / midwives", "4", "2", "0"],
        ["Pharmacy / laboratory staff", "1", "0", "0"],
        ["Other cadres", "0", "1", "0"],
        ["TOTAL", "8", "7", "0"],
    ])

    _add_banner(doc, "3.3", "Health workers trained in PEN-Plus", "Every quarter")
    _add_table(doc, [
        ["Cadre", "Female, this quarter", "Male, this quarter", "Not stated"],
        ["Medical doctors / specialists", "3", "4", "0"],
        ["Clinical officers / associates", "2", "2", "0"],
        ["Nurses / midwives", "6", "3", "1"],
        ["Pharmacy / laboratory staff", "1", "1", "0"],
        ["Other cadres", "0", "1", "0"],
        ["TOTAL", "12", "11", "1"],
    ])

    _add_banner(doc, "4. Health financing, medicines and service continuity", "Focus area 4")
    _add_banner(doc, "4.1", "Annual resource-mobilization round table", "Q4, or when held")
    _add_table(doc, [
        ["Item", "Response", "Date", "Meeting report or document title"],
        ["Round table held to mobilize resources for PEN-Plus or broader NCD services",
         "Yes", "2026-02", "round_table_report.pdf"],
        ["A PEN-Plus or severe NCD line exists in the government budget", "No", "-", "-"],
    ])
    _add_banner(doc, "", "Tracer medicines and diagnostics", "Every quarter")
    _add_table(doc, [
        ["Tracer item", "Availability across PEN-Plus sites",
         "Facilities with at least one day of stock-out this quarter"],
        ["Insulin", "Always available", "1"],
        ["Insulin syringes, pens or needles", "Sometimes available", "2"],
        ["Blood glucose test strips", "Always available", "0"],
        ["Hydroxyurea", "Never available", "5"],
        ["Benzathine benzylpenicillin", "Always available", "0"],
        ["Sickle cell rapid or confirmatory tests", "Sometimes available", "3"],
        ["HbA1c testing", "Not applicable", "-"],
        ["Echocardiography or ultrasound access", "Sometimes available", "4"],
    ])

    _add_banner(doc, "5. Health information, monitoring and data quality", "Focus area 5")
    _add_banner(doc, "5.1", "PEN-Plus indicators integrated into the national HMIS / DHIS2",
                "Integration: Q4")
    _add_table(doc, [
        ["Item", "Response"],
        ["Extent of integration into the national HMIS / DHIS2", "Partially integrated"],
        ["Number of PEN-Plus indicators configured", "8"],
        ["At least one full reporting period received through the national system", "Yes"],
        ["Frequency of data collection at first-referral level", "Monthly"],
        ["Frequency of data collection at primary care level, where applicable", "Quarterly"],
    ])
    _add_table(doc, [
        ["Change since the last return", "Response", "Details"],
        ["Change in definitions, source systems or deduplication method since the last return",
         "No", "-"],
        ["Correction to a previously reported figure", "No", "-"],
    ])
    _add_table(doc, [
        ["Data domain", "Confidence", "Main limitation", "Evidence held on file"],
        ["Facilities and coverage", "High", "-", "Yes"],
        ["Patients", "Medium", "Deduplication is manual", "Yes"],
        ["Workforce", "High", "-", "Yes"],
        ["Quality and mentorship", "Medium", "Not all sites assessed", "Yes"],
        ["Governance, financing, HMIS", "High", "-", "Yes"],
    ])

    _add_banner(doc, "6. Communication and visibility", "Focus area 6. Q4")
    _add_banner(doc, "6.1", "Communication and visibility products", "Q4")
    _add_table(doc, [
        ["Product type", "Number this year", "Language(s)", "Evidence / link or file reference"],
        ["Press releases / media stories", "2", "English, French", "press.pdf"],
        ["Videos / patient stories", "1", "English", "video.mp4"],
        ["Advocacy briefs / reports", "1", "English", "brief.pdf"],
        ["Social media campaigns / digital products", "3", "English, French", "campaign.pdf"],
        ["Other", "0", "-", "-"],
        ["TOTAL", "7", "-", "-"],
    ])
    _add_table(doc, [
        ["Safeguard", "Response"],
        ["Documented informed consent held for every product featuring a patient "
         "(and parent or guardian consent for minors)", "Yes"],
    ])

    doc.add_paragraph("Annex A. Facility register and quarterly facility return")
    doc.add_paragraph("Facility register")
    _add_table(doc, [
        ["Facility ID", "Facility name", "Region / province", "District", "Level",
         "Service start date", "Status", "Project-supported?", "Conditions managed"],
        ["GHA-0001", "Korle Bu Teaching Hospital", "Greater Accra", "Accra Metro", "Tertiary",
         "2023-01", "Operational", "Yes", "t1d,scd,rhd,severe_htn"],
        ["GHA-0002", "Komfo Anokye Teaching Hospital", "Ashanti", "Kumasi", "Tertiary",
         "2023-06", "Opened this period", "Partial", "t1d,scd"],
    ])
    doc.add_paragraph("Facility return this quarter")
    _add_table(doc, [
        ["Facility ID", "Facility name", "Return status", "Ever enrolled, four tracers",
         "Active in care, four tracers", "Mentorship visit this quarter?", "Quality score %",
         "All critical criteria met?", "Readiness class"],
        ["GHA-0001", "Korle Bu Teaching Hospital", "Yes", "120", "100", "Yes", "85", "Yes", "green"],
        ["GHA-0002", "Komfo Anokye Teaching Hospital", "Partial", "30", "25", "No", "-", "-",
         "amber"],
    ])

    doc.save(path)
