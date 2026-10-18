"""The new national quarterly tool (docs/refinement/03_reporting_form/), end to
end: parse a filled copy of the real template, load it, transform it."""
from __future__ import annotations

import transform
from fixtures.build_national_v4_return import build_national_v4_return
from load import connect, init_db, load_return
from parse import parse_return


def _gold(db_path):
    return {(g["indicator_code"], g["disagg_key"], g["disagg_value"]): g
            for g in connect(db_path).execute("SELECT * FROM gold_indicator WHERE iso3='GHA'")}


def test_new_tool_is_recognised_and_parsed(tmp_path):
    path = str(tmp_path / "GHA_2026_Q3.docx")
    build_national_v4_return(path)
    rec = parse_return(path)

    assert rec["form_version"] == "national_v4"
    assert rec["country_name"] == "Ghana"
    assert rec["period_id"] == "2026-Q3"
    assert rec["date_completed"] == "2026-10-20"
    # 2.5: one all-conditions row
    assert rec["context"]["patients_all_ever"] == 900
    assert rec["context"]["patients_all_new"] == 60
    # 2.6: sentinel cohort, ever / new / active per condition
    stock = {s["condition"]: s for s in rec["patient_stock"]}
    flow = {f["condition"]: f for f in rec["patient_flow"]}
    assert stock["t1d"] == {"condition": "t1d", "ever_enrolled": 300, "active_end": 280}
    assert flow["scd"]["new_enrolled"] == 30
    assert "severe_htn" not in stock
    # The printed retention % (350, an impossible value) is never read.
    assert rec["retention"] == []
    assert rec["retention_pct_reported"] == {}
    # 5.2 HMIS integration, and the validation inputs from 2.3 / 2.4 / 3.4
    assert rec["context"]["his_integration_level"] == 2
    assert rec["context"]["his_indicators_configured"] == 12
    assert rec["context"]["fac_initiated"] == 5
    assert rec["context"]["quality_met"] == 2
    assert rec["context"]["mentorship_num"] == 4
    assert rec["context"]["round_table_held"] == 1
    assert rec["facilities"][0]["status"] == "operational"


def test_new_tool_indicators(tmp_path):
    path = str(tmp_path / "GHA_2026_Q3.docx")
    build_national_v4_return(path)
    db_path = str(tmp_path / "store.db")
    con = init_db(db_path)
    load_return(con, parse_return(path), verdict="accepted")
    con.close()
    transform.build(db_path)
    gold = _gold(db_path)

    assert gold[("2.5", "all", "all")]["numerator"] == 900          # all PEN-Plus
    assert gold[("2.6", "all", "all")]["numerator"] == 800          # sentinel ever
    assert gold[("2.6a", "all", "all")]["numerator"] == 740         # sentinel active
    assert gold[("2.6", "measure", "new_this_period")]["numerator"] == 55
    # approximate retention: (740 - 55) / (800 - 55), never the printed 350%
    assert gold[("2.6b", "all", "all")]["numerator"] == 685
    assert gold[("2.6b", "all", "all")]["denominator"] == 745
    assert gold[("2.6b", "all", "all")]["value"] < 1
    assert gold[("5.2", "all", "all")]["numerator"] == 1
    assert gold[("5.2", "response", "yes")]["numerator"] == 1
    assert gold[("3.3", "all", "all")]["numerator"] == (1 + 2) + (5 + 1)
    assert ("5.1", "all", "all") not in gold                        # gone from the tool
