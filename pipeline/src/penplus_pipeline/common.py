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
#:
#: This is the real sixteen-indicator list from the Results Framework
#: (Phase_2_PEN-Plus_Reporting_Tools.docx, section 7's progress-summary
#: table gives the definitive sixteen codes), not the shorter, differently
#: coded list the data model workbook first shipped with. See
#: docs/architecture.md, "Indicator list corrected against the real
#: reporting forms", for what changed and why the form outranks the workbook
#: wherever the two disagree.
#:
#: `milestone` is the regional target this indicator is measured against,
#: from the traceability workbook. It stays None until the Regional Office
#: publishes the milestone value for that indicator; a screen must show that
#: state rather than a fabricated number (see docs/architecture.md,
#: "Milestones").
INDICATORS = [
    ("1.1", "PEN-Plus integrated into national NCD strategy and UHC agenda", "governance",
     "increase", "count",
     "Countries with the milestone achieved and a document named",
     "countries with status yes and a document title, over countries reporting", None),
    ("1.2", "PEN-Plus Plan developed, approved, launched and under implementation", "governance",
     "increase", "count",
     "Countries with the milestone achieved and a document named",
     "countries with status yes and a document title, over countries reporting", None),
    ("1.3", "Costed National Operational Plan on PEN-Plus developed and launched", "governance",
     "increase", "count",
     "Countries with the milestone achieved and a document named",
     "countries with status yes and a document title, over countries reporting", None),
    ("2.1", "National guidelines and protocols disseminated to all PEN-Plus sites", "service",
     "increase", "rate",
     "Tracer conditions with an adapted, validated protocol disseminated to every site",
     "count of the four tracers marked disseminated, over four", None),
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
     "numerator over denominator, by condition (reported alongside 2.6, not a"
     " seventeenth indicator)", None),
    ("3.1", "People completing a PEN-Plus WHO Academy course", "workforce", "increase", "count",
     "Cumulative course completions, pre-filled by WHO AFRO from the Academy system",
     "sum of female, male and not-stated completions", None),
    ("3.2", "Health workers trained as Trainers of Trainers", "workforce", "increase", "count",
     "Providers qualified to train others, cumulative by cadre",
     "sum of female, male and not-stated ToT trained, cumulative", None),
    ("3.3", "Health workers trained in PEN-Plus", "workforce", "increase", "count",
     "Providers trained at facility level this quarter, by cadre",
     "sum of female, male and not-stated trained this quarter", None),
    ("3.4", "Facilities with an active clinical mentorship programme", "quality", "increase", "rate",
     "Facilities with at least one documented mentorship visit in the quarter",
     "facilities with a mentorship visit this quarter over operational facilities", None),
    ("4.1", "Annual resource-mobilization round table", "financing", "increase", "count",
     "Countries that held a round table to mobilize resources for PEN-Plus this year",
     "countries with round table held = yes, over countries reporting", None),
    ("5.1", "Reporting completeness, timeliness and HMIS integration", "data", "increase", "rate",
     "Complete facility returns over facilities expected",
     "returns_complete over facilities_expected", None),
    ("6.1", "Communication and visibility products", "communication", "increase", "count",
     "Consent-safeguarded products published in the year",
     "sum of product counts across product types", None),
]


#: The five implementation phases and fourteen steps a country moves through
#: while scaling up PEN-Plus, transcribed verbatim from
#: Phase_1_PEN-Plus_Reporting_Tools.docx, section 3 "Four pillars and project
#: phases" (the second table, "PEN-Plus project phases"). This is a fixed
#: reference list, not per-country data -- per-country status lives in
#: fact_implementation_step, loaded from the round 1 monitoring workbook.
#:
#: Distinct from `funding_round` (the two Helmsley grant rounds a country
#: belongs to) and from the country-form indicators: a country can be
#: mid-scale-up on these phases regardless of which grant round it joined in.
#:
#: (step_no, phase_no, phase_label, step_label)
IMPLEMENTATION_STEPS = [
    (1, 1, "Phase 1. Assessment of the system and of facility readiness",
     "Conduct a comprehensive assessment of existing health care and facilities"),
    (2, 1, "Phase 1. Assessment of the system and of facility readiness",
     "SWOT analysis"),
    (3, 1, "Phase 1. Assessment of the system and of facility readiness",
     "Inventory available resources and determine capacities and potential gaps"),
    (4, 2, "Phase 2. Service delivery model",
     "Develop a robust service delivery model based on the assessment findings"),
    (5, 2, "Phase 2. Service delivery model",
     "Define protocols, guidelines and workflows for effective service delivery"),
    (6, 2, "Phase 2. Service delivery model",
     "Adapt the model to specific needs and challenges"),
    (7, 3, "Phase 3. Launch of implementation",
     "Deploy the planned interventions in selected pilot sites or communities"),
    (8, 4, "Phase 4. Monitoring",
     "Test the effectiveness and feasibility of the strategy in real conditions"),
    (9, 4, "Phase 4. Monitoring",
     "Pilot new protocols, organize training sessions and set up feedback mechanisms"),
    (10, 4, "Phase 4. Monitoring",
     "Implement a monitoring and evaluation framework to track progress"),
    (11, 4, "Phase 4. Monitoring",
     "Analyse data to assess impact and inform decision-making"),
    (12, 4, "Phase 4. Monitoring",
     "Progressively extend successful strategies to other sites or regions"),
    (13, 5, "Phase 5. National coverage above 60%",
     "Collaborate with national and regional stakeholders for coordination"),
    (14, 5, "Phase 5. National coverage above 60%",
     "Ensure sustainability through continuous monitoring, evaluation and adaptation"),
]

#: step_no -> phase_no, for deriving the highest phase a country has fully
#: completed (every step of that phase, and every phase before it, is 'yes').
STEP_PHASE = {step_no: phase_no for step_no, phase_no, _, _ in IMPLEMENTATION_STEPS}
PHASE_LABELS = {phase_no: label for _, phase_no, label, _ in IMPLEMENTATION_STEPS}


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
