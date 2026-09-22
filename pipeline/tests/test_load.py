"""Round-trip a rec through load_return, then the immutability/revision contract."""
from __future__ import annotations

import pytest
from load import load_return


def test_load_return_writes_every_fact_table(db, make_rec):
    rec = make_rec()
    rid = load_return(db, rec, verdict="accepted")

    ret = db.execute("SELECT * FROM fact_return WHERE return_id=?", (rid,)).fetchone()
    assert ret["iso3"] == "GHA"
    assert ret["period_id"] == "2026-Q1"
    assert ret["revision"] == 1
    assert ret["superseded"] == 0
    assert ret["verdict"] == "accepted"
    assert ret["source_kind"] == "form"

    stock = {r["condition"]: r for r in db.execute(
        "SELECT * FROM fact_patient_stock WHERE return_id=?", (rid,))}
    assert stock["t1d"]["ever_enrolled"] == 120
    assert stock["t1d"]["active_end"] == 100
    assert stock["other_reported"]["ever_enrolled"] is None
    assert stock["other_reported"]["active_end"] == 15

    flow = {r["condition"]: r for r in db.execute(
        "SELECT * FROM fact_patient_flow WHERE return_id=?", (rid,))}
    assert flow["t1d"]["new_enrolled"] == 10
    assert flow["severe_htn"]["died"] == 2

    age = list(db.execute(
        "SELECT * FROM fact_patient_age WHERE return_id=? ORDER BY age_band", (rid,)))
    assert len(age) == 3
    assert sum(a["patients"] for a in age) == 100

    wf = {r["cadre"]: r for r in db.execute(
        "SELECT * FROM fact_workforce WHERE return_id=?", (rid,))}
    assert wf["doctors"]["trained_f"] == 2
    assert wf["nurses_midwives"]["working_at_site"] == 18

    q = db.execute("SELECT * FROM fact_quality WHERE return_id=?", (rid,)).fetchone()
    assert q["facilities_expected"] == 10
    assert q["returns_complete"] == 8
    assert q["completeness"] == pytest.approx(0.8)

    ctx = {r["measure"]: r["value"] for r in db.execute(
        "SELECT measure, value FROM fact_context WHERE return_id=?", (rid,))}
    assert ctx["districts_total"] == 20
    assert ctx["tots"] == 5
    assert ctx["retention_num_t1d"] == 80
    assert ctx["retention_den_t1d"] == 100


def test_reloading_same_period_creates_revision_and_supersedes(db, make_rec):
    rec1 = make_rec()
    rid1 = load_return(db, rec1, verdict="accepted")

    rec2 = make_rec()
    rec2["patient_stock"][0]["ever_enrolled"] = 130  # a correction
    rid2 = load_return(db, rec2, verdict="accepted")

    assert rid2 != rid1

    rows = list(db.execute(
        "SELECT return_id, revision, superseded FROM fact_return"
        " WHERE iso3='GHA' AND period_id='2026-Q1' ORDER BY revision"))
    assert len(rows) == 2
    assert rows[0]["return_id"] == rid1
    assert rows[0]["superseded"] == 1
    assert rows[1]["return_id"] == rid2
    assert rows[1]["superseded"] == 0
    assert rows[1]["revision"] == 2

    live = list(db.execute(
        "SELECT return_id FROM fact_return"
        " WHERE iso3='GHA' AND period_id='2026-Q1' AND superseded=0"))
    assert len(live) == 1
    assert live[0]["return_id"] == rid2

    # the old revision's facts are untouched, not deleted
    old_stock = db.execute(
        "SELECT ever_enrolled FROM fact_patient_stock WHERE return_id=? AND condition='t1d'",
        (rid1,)).fetchone()
    assert old_stock["ever_enrolled"] == 120
