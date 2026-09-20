"""Shared reference data. One place for country codes and the condition map."""

COUNTRIES = {
    "Angola": ("AGO", "phase_2"), "Benin": ("BEN", "phase_1"),
    "Botswana": ("BWA", "phase_2"), "Burkina Faso": ("BFA", "phase_1"),
    "Burundi": ("BDI", "phase_2"), "Cabo Verde": ("CPV", "phase_2"),
    "Cameroon": ("CMR", "phase_1"),
    "Democratic Republic of the Congo": ("COD", "phase_1"),
    "Republic of the Congo": ("COG", "phase_1"), "Congo": ("COG", "phase_1"),
    "Eswatini": ("SWZ", "phase_2"), "Ethiopia": ("ETH", "phase_1"),
    "Gabon": ("GAB", "phase_2"), "The Gambia": ("GMB", "phase_2"),
    "Gambia": ("GMB", "phase_2"), "Ghana": ("GHA", "phase_1"),
    "Kenya": ("KEN", "phase_1"), "Lesotho": ("LSO", "phase_1"),
    "Liberia": ("LBR", "phase_1"), "Malawi": ("MWI", "phase_1"),
    "Mali": ("MLI", "phase_2"), "Mozambique": ("MOZ", "phase_1"),
    "Niger": ("NER", "phase_1"), "Nigeria": ("NGA", "phase_1"),
    "Rwanda": ("RWA", "phase_1"), "Senegal": ("SEN", "phase_2"),
    "Sierra Leone": ("SLE", "phase_1"), "South Sudan": ("SSD", "phase_2"),
    "Togo": ("TGO", "phase_2"),
    "United Republic of Tanzania": ("TZA", "phase_1"), "Tanzania": ("TZA", "phase_1"),
    "Uganda": ("UGA", "phase_1"), "Zambia": ("ZMB", "phase_1"),
    "Zimbabwe": ("ZWE", "phase_1"),
}

# The four tracer conditions of Phase Two. Everything else is reported once,
# outside the regional total, under other_reported.
TRACERS = ["t1d", "scd", "rhd", "severe_htn"]

ICPPA_CONDITION_MAP = {
    "Sickle cell disease": "scd",
    "Type 1 diabetes": "t1d",
    "Rheumatic heart disease": "rhd",
    "Severe hypertension": "severe_htn",
    "Type 2 diabetes": "other_reported",
    "Diabetes (types combined)": "other_reported",
    "Congenital heart disease": "other_reported",
    "Cardiomyopathy": "other_reported",
    "Asthma / COPD": "other_reported",
    "Other conditions": "other_reported",
}

ICPPA_CADRE_MAP = {
    "Medical doctors": "doctors",
    "Clinical officers / CHO": "clinical_officers",
    "Nurses (incl. physician assistants)": "nurses_midwives",
    "Laboratory staff": "pharmacy_lab",
    "Administrative / allied / other": "other",
    "Cadre split not reported": "other",
}

#: (code, label_en, family, direction, unit, definition, formula, milestone)
#: `milestone` is the regional target this indicator is measured against, from
#: the traceability workbook. It stays None until the Regional Office publishes
#: the milestone value for that indicator; a screen must show that state rather
#: than a fabricated number (see docs/architecture.md, "Milestones").
INDICATORS = [
    ("2.2", "Secondary-level facilities assessed for readiness", "capacity", "increase", "count",
     "Facilities assessed with the AFRO readiness tool during the year",
     "count of facilities with a readiness class", None),
    ("2.3", "Health facilities initiating PEN-Plus services", "capacity", "increase", "count",
     "Facilities capacitated and offering PEN-Plus services",
     "count of facilities with status operational or started_this_period", None),
    ("2.4", "Facilities achieving PEN-Plus quality standards", "quality", "increase", "rate",
     "Facilities scoring at least 80 per cent with all critical criteria met",
     "numerator over facilities assessed against the checklist", None),
    ("2.5", "Unique patients ever enrolled", "service", "increase", "count",
     "Cumulative patients since services began, deduplicated at facility level",
     "sum of ever_enrolled over the four tracers", None),
    ("2.6", "Patients enrolled and active in care", "service", "increase", "count",
     "Patients not lost, transferred, stopped or deceased",
     "sum of active_end over the four tracers", None),
    ("2.6b", "Twelve-month retention rate", "service", "increase", "rate",
     "Cohort patients with a visit in the period over the cohort minus exits",
     "numerator over denominator, by condition", None),
    ("3.2", "Health workers trained as Trainers of Trainers", "workforce", "increase", "count",
     "Providers qualified to train others", "trained this period flagged as ToT", None),
    ("3.3", "Health workers trained in PEN-Plus", "workforce", "increase", "count",
     "Providers trained at facility level", "sum of trained across the periods of the year", None),
    ("3.4", "Facilities with an active clinical mentorship programme", "quality", "increase", "rate",
     "Facilities with at least one documented mentorship visit in the period",
     "facilities with months_mentorship at least 1 over operational facilities", None),
    ("5.1", "Reporting completeness", "data", "increase", "rate",
     "Complete facility returns over facilities expected",
     "returns_complete over facilities_expected", None),
]


def resolve_iso3(country_name: str) -> str:
    """Look up the ISO3 code for a country name on the return, or raise.

    Shared by load.py (to key a return) and validate.py (to look up its
    reporting history), so the two never risk disagreeing on the mapping.
    """
    if not country_name:
        raise ValueError("no country on the return")
    entry = COUNTRIES.get(country_name.strip())
    if not entry:
        raise ValueError(f"country not in the Phase Two list: {country_name}")
    return entry[0]
