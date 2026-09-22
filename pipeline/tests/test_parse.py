"""parse_return() against a programmatically generated, synthetic .docx.

See tests/fixtures/build_synthetic_return.py: it is not a real country return,
just a structurally faithful document built for this test, matching the real
Phase_2_PEN-Plus_Reporting_Tools.docx (v3) section structure.
"""
from __future__ import annotations

import pytest
from fixtures.build_synthetic_return import build_synthetic_return
from parse import parse_return


@pytest.fixture
def synthetic_return_path(tmp_path):
    path = str(tmp_path / "GHA_2026_Q1_PENPLUS_synthetic.docx")
    build_synthetic_return(path)
    return path


@pytest.fixture
def broken_return_path(tmp_path):
    path = str(tmp_path / "BROKEN_no_section0.docx")
    build_synthetic_return(path, broken=True)
    return path


def test_parse_identification(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    assert rec["country_name"] == "Ghana"
    assert rec["period_id"] == "2026-Q1"
    assert rec["quarter_id"] == "2026-Q1"
    assert rec["rhythm"] == "quarterly"
    assert rec["closing_date"] == "2026-03-31"
    assert rec["first_return"] == "no"


def test_parse_national_context_and_completeness(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    assert rec["context"]["districts_total"] == 20
    assert rec["context"]["districts_with_penplus"] == 10
    assert rec["quality"]["facilities_expected"] == 10
    assert rec["quality"]["returns_complete"] == 8
    assert rec["quality"]["returns_on_time"] == 7


def test_parse_governance_fixed_codes(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    assert len(rec["governance"]) == 3
    g = {r["milestone_code"]: r for r in rec["governance"]}
    assert g["1.1"]["status"] == "yes"
    assert g["1.1"]["achieved_in"] == "2024"
    assert g["1.1"]["document"] == "strategy.pdf"
    assert g["1.2"]["status"] == "under_development"
    assert g["1.2"]["achieved_in"] is None  # "-" -> None
    assert g["1.3"]["status"] == "no"


def test_parse_guideline_dissemination(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    assert rec["context"]["guideline_disseminated_t1d"] == 1
    assert rec["context"]["guideline_disseminated_scd"] == 0
    assert rec["context"]["guideline_disseminated_rhd"] == 0
    assert rec["context"]["guideline_disseminated_severe_htn"] == 1


def test_parse_patient_stock_and_null_discipline(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    stock = {s["condition"]: s for s in rec["patient_stock"]}

    assert stock["t1d"]["ever_enrolled"] == 150
    assert stock["t1d"]["active_end"] == 140

    # "NR" -> None (never 0)
    assert stock["scd"]["ever_enrolled"] is None
    assert stock["scd"]["active_end"] == 60

    # "-" -> None
    assert stock["rhd"]["ever_enrolled"] == 45
    assert stock["rhd"]["active_end"] is None

    # "Not reported" -> None
    assert stock["severe_htn"]["ever_enrolled"] is None
    assert stock["severe_htn"]["active_end"] == 190

    # The form's own "TOTAL, four tracer conditions" row does not match the
    # bare "total" key and is correctly left unparsed: nothing downstream
    # reads it, so it must not silently reappear as a fifth condition.
    assert "total" not in stock


def test_parse_retention(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    ret = {r["condition"]: r for r in rec["retention"]}
    assert ret["t1d"]["numerator"] == 80
    assert ret["t1d"]["denominator"] == 100
    assert "scd" not in ret  # both cells were "-": nothing to report
    assert rec["ltfu_compliant"] == 1  # "Regional 90-day rule" -> compliant


def test_parse_patient_flow_optional_block(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    flow = {f["condition"]: f for f in rec["patient_flow"]}
    assert flow["t1d"]["new_enrolled"] == 20
    assert flow["t1d"]["ltfu"] == 3
    assert flow["severe_htn"]["died"] == 3
    # the optional "other severe NCDs" row is captured too, all null here
    assert "other_reported" in flow
    assert flow["other_reported"]["new_enrolled"] is None
    assert len(flow) == 5


def test_parse_who_academy(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    assert rec["context"]["who_academy_f"] == 6
    assert rec["context"]["who_academy_m"] == 4
    assert rec["context"]["who_academy_ns"] == 0


def test_parse_tot_by_cadre(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    tot = {w["cadre"]: w for w in rec["workforce_tot"]}
    assert tot["doctors"]["trained_f"] == 2
    assert tot["doctors"]["trained_m"] == 3
    assert "total" not in tot  # the form's own TOTAL row is not a cadre


def test_parse_quarterly_workforce(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    wf = {w["cadre"]: w for w in rec["workforce"]}
    assert wf["doctors"]["trained_f"] == 3
    assert wf["doctors"]["trained_m"] == 4
    assert wf["nurses_midwives"]["trained_ns"] == 1


def test_parse_round_table_and_supply(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    assert rec["context"]["round_table_held"] == 1
    assert rec["context"]["budget_line_exists"] == 0
    supply = {s["item"]: s for s in rec["supply"]}
    assert supply["Insulin"]["availability"] == "always"
    assert supply["Hydroxyurea"]["facilities_stockout"] == 5


def test_parse_his_integration_and_confidence(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    assert rec["context"]["his_integration_level"] == 1  # partially integrated
    assert rec["confidence"]["facilities_and_coverage"] == "High"
    assert rec["confidence"]["quality_and_mentorship"] == "Medium"
    assert rec["confidence"]["governance_financing_hmis"] == "High"


def test_parse_communication_products(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    assert rec["context"]["comm_products_total"] == 7
    assert rec["context"]["comm_consent_confirmed"] == 1


def test_parse_facility_register_columns_not_swapped(synthetic_return_path):
    """Annex A's register lists region before district; getting this backwards
    silently mislabels every facility's geography."""
    rec = parse_return(synthetic_return_path)
    f1, f2 = rec["facilities"]
    assert f1["facility_id"] == "GHA-0001"
    assert f1["region"] == "Greater Accra"
    assert f1["district"] == "Accra Metro"
    assert f1["status"] == "operational"
    assert f1["project_supported"] == "yes"
    assert f2["status"] == "started_this_period"
    assert f2["project_supported"] == "partial"


def test_parse_facility_return_mentorship_is_yes_no(synthetic_return_path):
    """The v3 form asks a quarterly yes/no, not a 0-3 month count."""
    rec = parse_return(synthetic_return_path)
    fp = {f["facility_id"]: f for f in rec["facility_period"]}
    assert fp["GHA-0001"]["mentorship_visit"] == 1
    assert fp["GHA-0002"]["mentorship_visit"] == 0
    assert fp["GHA-0001"]["readiness_class"] == "green"
    assert fp["GHA-0001"]["quality_score"] == 85


def test_parse_rejects_return_missing_section0(broken_return_path):
    with pytest.raises(ValueError):
        parse_return(broken_return_path)
