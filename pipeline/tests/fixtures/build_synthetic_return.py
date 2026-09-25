"""
build_synthetic_return.py - generates a SYNTHETIC .docx fixture for testing parse.py only.

This is not a real WHO AFRO country return. Every name, figure and identifier
below is invented for the test suite. It exists so test_parse.py can exercise
index_tables()/rows_of()/by_label() against a structurally faithful document
without checking a binary .docx into the repository. Do not copy this data
into seed_history.py or anywhere a real return is expected.

Layout mirrors Phase_2_PEN-Plus_Reporting_Tools.docx, the real form this
build was corrected against (see docs/architecture.md and
docs/reporting-form.md): section banners are one-row tables ("N. Title" for a
top-level section, "Indicator N.M | Title | RF frequency" for a sub-indicator
-- the sub-indicator cell reads "Indicator N.M", not the bare code the
previous copy of the form used). Annex A holds a single facility-register
table; the facility-level performance columns that used to sit alongside it
moved to the separate monthly facility return, not exercised here.
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
    """Write a synthetic PEN-Plus return .docx to `path`.

    broken=True omits Section 0 entirely, to exercise parse_return()'s
    "reject a structurally altered return" ValueError.
    """
    doc = Document()

    if not broken:
        _add_banner(doc, "0. Identification and reporting completeness", "")
        _add_table(doc, [
            ["Field", "Entry"],
            ["Country", "Ghana"],
            ["Reporting quarter", "Quarter 1"],
            ["Period covered (from - to)", "2026-01-01 to 2026-03-31"],
            ["Year", "2026"],
            ["NPO / WHO Country Office focal point", "Jane Doe"],
            ["National programme focal point", "John Smith"],
            ["M&E focal point", "Focal Person"],
            ["Date completed", "2026-04-10"],
        ])
        _add_table(doc, [
            ["Item", "Count"],
            ["Health districts in the country", "20"],
            ["First-referral / district hospitals in the country", "15"],
            ["Health districts where PEN-Plus services are offered", "10"],
            ["PEN-Plus facilities expected to report this quarter", "10"],
            ["Facilities submitting a complete return", "8"],
            ["Facilities submitting a partial return", "1"],
            ["Facilities submitting no return", "1"],
        ])
    else:
        # A deliberately broken document: no Section 0 heading anywhere.
        doc.add_paragraph("Some unrelated cover note")

    _add_banner(doc, "1. Governance and leadership", "Focus area 1")
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
    _add_banner(doc, "Indicator 2.1", "National guidelines / protocols adapted, validated and disseminated")
    _add_table(doc, [
        ["Condition", "Adapted & validated?", "Disseminated to all PEN-Plus sites?",
         "Document title / date"],
        ["Type 1 diabetes", "Yes", "Yes", "t1d_protocol.pdf"],
        ["Sickle cell disease", "Yes", "No", "scd_protocol.pdf"],
        ["Rheumatic heart disease", "No", "No", "-"],
        ["Other PEN-Plus condition (specify)", "-", "-", "-"],
    ])

    _add_banner(doc, "Indicator 2.5", "Unique patients ever enrolled")
    _add_table(doc, [
        ["Priority condition", "Ever enrolled, cumulative", "Newly enrolled this quarter"],
        ["Type 1 diabetes", "150", "20"],
        ["Sickle cell disease", "NR", "10"],            # NR -> None
        ["Rheumatic heart disease", "45", "5"],
        ["TOTAL - unique priority-condition patients", "195", "35"],
    ])

    _add_banner(doc, "Indicator 2.6", "Patients active in care and 12-month retention")
    _add_table(doc, [
        ["Priority condition", "Active in care at end of quarter", "Retention numerator",
         "Retention denominator", "Retention %"],
        ["Type 1 diabetes", "140", "80", "100", "80"],
        ["Sickle cell disease", "60", "-", "-", "-"],
        ["Rheumatic heart disease", "-", "-", "-", "-"],
        ["TOTAL - unique priority-condition patients", "200", "80", "100", "80"],
    ])
    _add_table(doc, [
        ["Condition", "Lost to follow-up", "Transferred out", "Stopped treatment", "Died"],
        ["Type 1 diabetes", "3", "1", "0", "2"],
        ["Sickle cell disease", "1", "0", "0", "1"],
        ["Rheumatic heart disease", "0", "0", "0", "0"],
        ["Other severe NCDs managed in PEN-Plus clinics", "-", "-", "-", "-"],
    ])

    _add_banner(doc, "3. Capacity building and workforce development", "Focus area 3")
    _add_banner(doc, "Indicator 3.1", "WHO Academy PEN-Plus course completion")
    _add_table(doc, [
        ["Measure", "Female", "Male", "Other / not stated", "Total"],
        ["People completing a PEN-Plus WHO Academy course - cumulative", "6", "4", "0", "10"],
    ])

    _add_banner(doc, "Indicator 3.2", "Health workers trained as Trainers of Trainers")
    _add_table(doc, [
        ["Cadre", "Female cumulative", "Male cumulative", "Other / not stated", "Total cumulative"],
        ["Medical doctors / specialists", "2", "3", "0", "5"],
        ["Clinical officers / associates", "1", "1", "0", "2"],
        ["Nurses / midwives", "4", "2", "0", "6"],
        ["Pharmacy / laboratory staff", "1", "0", "0", "1"],
        ["Other cadres", "0", "1", "0", "1"],
        ["TOTAL", "8", "7", "0", "15"],
    ])

    _add_banner(doc, "Indicator 3.3", "Health workers trained in PEN-Plus")
    _add_table(doc, [
        ["Cadre", "Female trained this quarter", "Male trained this quarter",
         "Total trained this quarter", "Year-to-date total"],
        ["Medical doctors / specialists", "3", "4", "7", "20"],
        ["Clinical officers / associates", "2", "2", "4", "12"],
        ["Nurses / midwives", "6", "3", "9", "28"],
        ["Pharmacy / laboratory staff", "1", "1", "2", "6"],
        ["Other cadres", "0", "1", "1", "3"],
        ["TOTAL", "12", "11", "23", "69"],
    ])

    _add_banner(doc, "4. Health financing, medicines and service continuity", "Focus area 4")
    _add_banner(doc, "Indicator 4.1", "Annual resource-mobilization round table")
    _add_table(doc, [
        ["Item", "Response", "Evidence / date"],
        ["Annual round table held to mobilize resources for PEN-Plus or broader NCD services",
         "Yes", "round_table_report.pdf"],
    ])
    _add_table(doc, [
        ["Tracer item", "Available across all PEN-Plus sites?",
         "Facilities with at least one day stock-out this quarter"],
        ["Insulin", "Always available", "1"],
        ["Insulin delivery supplies / syringes / needles", "Sometimes available", "2"],
        ["Blood glucose test strips", "Always available", "0"],
        ["Hydroxyurea", "Never available", "5"],
        ["Benzathine benzylpenicillin", "Always available", "0"],
        ["Sickle cell rapid / confirmatory tests", "Sometimes available", "3"],
        ["HbA1c testing", "Not applicable", "-"],
        ["Echocardiography / ultrasound access", "Sometimes available", "4"],
    ])

    _add_banner(doc, "5. Monitoring, evaluation and data quality", "Focus area 5")
    _add_banner(doc, "Indicator 5.1", "PEN-Plus indicators integrated in national HMIS / DHIS2")
    _add_table(doc, [
        ["Item", "Response"],
        ["PEN-Plus indicators integrated / configured in the national HMIS / DHIS2",
         "Partially integrated"],
        ["Number of PEN-Plus indicators configured", "8"],
        ["At least one full reporting period received through the national system", "Yes"],
        ["Reporting completeness for this quarter (%)", "90"],
        ["Reporting timeliness for this quarter (%)", "70"],
        ["Frequency of data collection at first-referral level", "Monthly"],
        ["Frequency of data collection at primary-care level, where applicable", "Quarterly"],
    ])
    _add_table(doc, [
        ["Check", "Result / explanation"],
        ["Facility counts in Annex A reconcile with indicator 2.3", "Yes"],
        ["Patient totals reconcile with indicators 2.5 and 2.6", "Yes"],
        ["Mentorship totals reconcile with indicator 3.4", "Yes"],
        ["Any change in definitions, source systems or deduplication method since last return", "No"],
        ["Any correction to a previously reported figure", "No"],
    ])
    _add_table(doc, [
        ["Data domain", "Confidence (High / Medium / Low)", "Main limitation", "Evidence held on file"],
        ["Facilities and coverage", "High", "-", "Yes"],
        ["Patients", "Medium", "Deduplication is manual", "Yes"],
        ["Workforce", "High", "-", "Yes"],
        ["Quality / mentorship", "Medium", "Not all sites assessed", "Yes"],
        ["Governance / financing / HMIS", "High", "-", "Yes"],
    ])

    _add_banner(doc, "6. Communication and visibility", "Focus area 6")
    _add_banner(doc, "Indicator 6.1", "Communication and visibility products published / disseminated")
    _add_table(doc, [
        ["Product type", "Number published / disseminated this year", "Language(s)",
         "Evidence / link or file reference"],
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

    _add_banner(doc, "Annex A.  Facility register", "")
    _add_banner(doc, "Facility register", "Update only when a facility changes")
    _add_table(doc, [
        ["Facility ID", "Facility name", "Region / province", "District", "Level",
         "Service start date", "Status", "Project-supported?", "Conditions managed"],
        ["GHA-0001", "Korle Bu Teaching Hospital", "Greater Accra", "Accra Metro", "Tertiary",
         "2023-01", "Operational", "Yes", "t1d,scd,rhd"],
        ["GHA-0002", "Komfo Anokye Teaching Hospital", "Ashanti", "Kumasi", "Tertiary",
         "2023-06", "Opened this period", "Partial", "t1d,scd"],
    ])

    doc.save(path)
