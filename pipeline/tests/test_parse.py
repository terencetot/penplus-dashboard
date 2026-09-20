"""parse_return() against a programmatically generated, synthetic .docx.

See tests/fixtures/build_synthetic_return.py: it is not a real country return,
just a structurally faithful document built for this test.
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
    path = str(tmp_path / "BROKEN_no_section1.docx")
    build_synthetic_return(path, broken=True)
    return path


def test_parse_identification(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    assert rec["country_name"] == "Ghana"
    assert rec["period_id"] == "2026-Q1"
    assert rec["quarter_id"] == "2026-Q1"
    assert rec["rhythm"] == "quarterly"
    assert rec["closing_date"] == "2026-03-31"
    assert rec["days_in_period"] == 90


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

    assert stock["total"]["ever_enrolled"] == 640
    assert stock["total"]["active_end"] == 640

    # other_reported is always appended, even with no "patients outside" table
    assert stock["other_reported"]["ever_enrolled"] is None
    assert stock["other_reported"]["active_end"] is None


def test_parse_patient_flow(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    flow = {f["condition"]: f for f in rec["patient_flow"]}
    assert flow["t1d"]["new_enrolled"] == 20
    assert flow["t1d"]["ltfu"] == 3
    assert flow["severe_htn"]["died"] == 3
    assert len(flow) == 4


def test_parse_workforce(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    wf = {w["cadre"]: w for w in rec["workforce"]}
    assert wf["doctors"]["trained_f"] == 3
    assert wf["doctors"]["trained_m"] == 4
    assert wf["nurses_midwives"]["working_at_site"] == 22
    assert wf["total"]["fully_trained"] == 51


def test_parse_governance(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    assert len(rec["governance"]) == 2
    adopted = rec["governance"][0]
    assert adopted["milestone"] == "National PEN-Plus strategy adopted"
    assert adopted["status"] == "yes"
    assert adopted["achieved_in"] == "2024"
    assert adopted["document"] == "strategy.pdf"
    plan = rec["governance"][1]
    assert plan["status"] == "under_development"
    assert plan["achieved_in"] is None  # "-" -> None


def test_parse_facilities_annex(synthetic_return_path):
    rec = parse_return(synthetic_return_path)
    assert len(rec["facilities"]) == 2
    f1, f2 = rec["facilities"]
    assert f1["facility_id"] == "GHA-0001"
    assert f1["name"] == "Korle Bu Teaching Hospital"
    assert f1["status"] == "operational"
    assert f1["project_supported"] == "yes"
    assert f2["status"] == "started_this_period"
    assert f2["project_supported"] == "partial"


def test_parse_rejects_return_missing_section1(broken_return_path):
    with pytest.raises(ValueError):
        parse_return(broken_return_path)
