"""transform.build() rebuilds gold_indicator from fact_return. transform.build()
opens its own connection to db_path, so these tests use a real temp file
(":memory:" would give it an empty, unrelated database) and set up the store
through init_db()/load_return() first, mirroring run.py.
"""
from __future__ import annotations

import transform
from load import connect, init_db, load_return


def test_held_return_excluded_from_gold(tmp_path, make_rec):
    db_path = str(tmp_path / "store.db")
    con = init_db(db_path)

    ok = make_rec(country_name="Ghana", period_id="2026-Q1", quarter_id="2026-Q1")
    load_return(con, ok, verdict="accepted")

    held = make_rec(country_name="Kenya", period_id="2026-Q1", quarter_id="2026-Q1")
    load_return(con, held, verdict="hold")
    con.close()

    transform.build(db_path)

    check = connect(db_path)
    gold = list(check.execute("SELECT * FROM gold_indicator"))
    assert any(g["iso3"] == "GHA" for g in gold)
    assert not any(g["iso3"] == "KEN" for g in gold)


def test_all_none_stock_produces_none_numerator_not_zero(tmp_path, make_rec):
    db_path = str(tmp_path / "store.db")
    con = init_db(db_path)

    rec = make_rec(country_name="Nigeria", period_id="2026-Q1", quarter_id="2026-Q1")
    for s in rec["patient_stock"]:
        s["ever_enrolled"] = None
        s["active_end"] = None
    load_return(con, rec, verdict="accepted")
    con.close()

    transform.build(db_path)

    check = connect(db_path)
    row = check.execute(
        "SELECT * FROM gold_indicator WHERE iso3='NGA' AND indicator_code='2.5'"
        " AND disagg_key='all'").fetchone()
    assert row["numerator"] is None
    assert row["value"] is None

    row26 = check.execute(
        "SELECT * FROM gold_indicator WHERE iso3='NGA' AND indicator_code='2.6'"
        " AND disagg_key='all'").fetchone()
    assert row26["numerator"] is None
    assert row26["value"] is None


def test_suppression_applies_to_disaggregated_not_to_all(tmp_path, make_rec):
    db_path = str(tmp_path / "store.db")
    con = init_db(db_path)

    rec = make_rec(country_name="Rwanda", period_id="2026-Q1", quarter_id="2026-Q1")
    rec["patient_stock"] = [
        {"condition": "t1d", "ever_enrolled": 3, "active_end": 3},
        {"condition": "scd", "ever_enrolled": None, "active_end": None},
        {"condition": "rhd", "ever_enrolled": None, "active_end": None},
        {"condition": "severe_htn", "ever_enrolled": None, "active_end": None},
    ]
    # keep age reconciliation happy for t1d (bands sum to active_end=3)
    rec["patient_age"] = [{"condition": "t1d", "age_band": "u15", "patients": 3}]
    load_return(con, rec, verdict="accepted")
    con.close()

    transform.build(db_path)

    check = connect(db_path)
    country_total = check.execute(
        "SELECT * FROM gold_indicator WHERE iso3='RWA' AND indicator_code='2.5'"
        " AND disagg_key='all'").fetchone()
    assert country_total["numerator"] == 3
    assert country_total["suppressed"] == 0

    disagg = check.execute(
        "SELECT * FROM gold_indicator WHERE iso3='RWA' AND indicator_code='2.5'"
        " AND disagg_key='condition' AND disagg_value='t1d'").fetchone()
    assert disagg["numerator"] == 3
    assert disagg["suppressed"] == 1


def test_stock_is_read_per_period_never_summed_across_periods(tmp_path, make_rec):
    db_path = str(tmp_path / "store.db")
    con = init_db(db_path)

    q1 = make_rec(country_name="Ghana", period_id="2026-Q1", quarter_id="2026-Q1")
    load_return(con, q1, verdict="accepted")

    q2 = make_rec(country_name="Ghana", period_id="2026-Q2", quarter_id="2026-Q2")
    for s in q2["patient_stock"]:
        if s["condition"] == "t1d":
            s["ever_enrolled"] = 130
            s["active_end"] = 105
    load_return(con, q2, verdict="accepted")
    con.close()

    transform.build(db_path)

    check = connect(db_path)
    expected_q1 = 120 + 80 + 40 + 200  # tracer ever_enrolled in the base fixture
    expected_q2 = 130 + 80 + 40 + 200

    g_q1 = check.execute(
        "SELECT numerator FROM gold_indicator WHERE iso3='GHA' AND period_id='2026-Q1'"
        " AND indicator_code='2.5' AND disagg_key='all'").fetchone()
    g_q2 = check.execute(
        "SELECT numerator FROM gold_indicator WHERE iso3='GHA' AND period_id='2026-Q2'"
        " AND indicator_code='2.5' AND disagg_key='all'").fetchone()

    assert g_q1["numerator"] == expected_q1
    assert g_q2["numerator"] == expected_q2
    # not cumulative: Q2's figure is not Q1 + Q2's own tracers
    assert g_q2["numerator"] != expected_q1 + expected_q2
