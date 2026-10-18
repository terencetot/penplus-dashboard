"""export.export() writes the static JSON bundle. Uses real temp files for the
same reason as test_transform.py: transform.build()/export.export() each open
their own connection to db_path, so ":memory:" would not share data."""
from __future__ import annotations

import json

import baseline
import export
import transform
from load import connect, init_db, load_return
from validate import Finding, record_findings


def _build_store(tmp_path, make_rec):
    db_path = str(tmp_path / "store.db")
    con = init_db(db_path)
    rec = make_rec(country_name="Ghana", period_id="2026-Q1", quarter_id="2026-Q1")
    rid = load_return(con, rec, verdict="accepted")
    record_findings(con, rid, [
        Finding("Medium", "2.1", "test finding", "observed", "expected", "a question?"),
    ])
    con.close()
    transform.build(db_path)
    return db_path


def _build_store_with_facility(tmp_path, make_rec):
    db_path = str(tmp_path / "store.db")
    con = init_db(db_path)
    rec = make_rec(
        country_name="Ghana", period_id="2026-Q1", quarter_id="2026-Q1",
        facilities=[{"facility_id": "GHA-0001", "name": "Ridge Regional Hospital",
                     "district": "Accra Metro", "region": "Greater Accra",
                     "status": "operational", "project_supported": "yes"}],
        facility_period=[{"facility_id": "GHA-0001", "return_received": "yes",
                           "active_end": 3, "quality_score": 40, "critical_met": "no",
                           "readiness_class": "amber"}],
    )
    load_return(con, rec, verdict="accepted")
    con.close()
    transform.build(db_path)
    return db_path


def test_non_public_export_keeps_facility_identity(tmp_path, make_rec):
    db_path = _build_store_with_facility(tmp_path, make_rec)
    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir), public=False)

    facilities = json.loads((out_dir / "facilities.json").read_text(encoding="utf-8"))
    assert facilities["rows"][0]["name"] == "Ridge Regional Hospital"
    assert facilities["manifest"]["public"] is False


def test_public_export_blanks_suppressed_cells_but_keeps_the_regional_total(tmp_path, make_rec):
    """A country reporting a small, individually-suppressed number must still
    count toward the regional aggregate -- suppression hides the country-level
    figure from the public build, it does not remove real evidence from the
    regional total (CLAUDE.md rule 7, and export.py's regional_value/headline,
    which read the un-redacted gold rows before any redaction is applied)."""
    db_path = str(tmp_path / "store.db")
    con = init_db(db_path)
    small = make_rec(
        country_name="Ghana", period_id="2026-Q1", quarter_id="2026-Q1",
        patient_stock=[
            {"condition": "t1d", "ever_enrolled": 3, "active_end": 2},
            {"condition": "scd", "ever_enrolled": None, "active_end": None},
            {"condition": "rhd", "ever_enrolled": None, "active_end": None},
            {"condition": "severe_htn", "ever_enrolled": None, "active_end": None},
        ],
    )
    load_return(con, small, verdict="accepted")
    con.close()
    transform.build(db_path)

    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir), public=True)

    indicators = json.loads((out_dir / "indicators.json").read_text(encoding="utf-8"))
    row_25 = next(v for v in indicators["values"]
                  if v["indicator_code"] == "2.6" and v["disagg_key"] == "condition"
                  and v["disagg_value"] == "t1d")
    assert row_25["suppressed"] == 1
    assert row_25["numerator"] is None  # withheld, not just flagged

    dim = next(d for d in indicators["dim"] if d["indicator_code"] == "2.6")
    assert dim["regional_value"] == 3  # the real number still feeds the regional total


def test_export_writes_expected_files_as_valid_json(tmp_path, make_rec):
    db_path = _build_store(tmp_path, make_rec)
    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir))

    expected = ["manifest.json", "overview.json", "indicators.json",
                "quality.json", "facilities.json", "countries/GHA.json"]
    loaded = {}
    for name in expected:
        p = out_dir / name
        assert p.exists(), f"{name} missing"
        assert p.stat().st_size > 0
        loaded[name] = json.loads(p.read_text(encoding="utf-8"))

    assert loaded["manifest.json"]["suppress_below"] == 5
    assert loaded["overview.json"]["manifest"]["form_version"]
    assert loaded["indicators.json"]["dim"]
    assert loaded["countries/GHA.json"]["country"]["iso3"] == "GHA"


def test_milestone_strip_has_five_entries_with_null_gap(tmp_path, make_rec):
    db_path = _build_store(tmp_path, make_rec)
    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir))

    overview = json.loads((out_dir / "overview.json").read_text(encoding="utf-8"))
    strip = overview["milestone_strip"]
    assert len(strip) == 5
    for entry in strip:
        # dim_indicator.milestone is None until published, so gap must be None
        # even where a value exists (see export.py's comment on HEADLINE_INDICATORS).
        assert entry["milestone"] is None
        assert entry["gap"] is None


def test_public_export_keeps_facility_names_by_default(tmp_path, make_rec):
    """Refinement v2 default: PUBLISH_FACILITY_NAMES = True. Facility names
    are public hospitals named at a public conference; small patient counts
    are still suppressed (CLAUDE.md rule 7)."""
    db_path = _build_store_with_facility(tmp_path, make_rec)
    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir), public=True)
    facilities = json.loads((out_dir / "facilities.json").read_text(encoding="utf-8"))
    assert facilities["rows"][0]["name"] == "Ridge Regional Hospital"
    assert facilities["manifest"]["publish_facility_names"] is True


def test_public_export_withholds_facility_identity_when_the_flag_is_off(tmp_path, make_rec,
                                                                        monkeypatch):
    monkeypatch.setattr(export, "PUBLISH_FACILITY_NAMES", False)
    db_path = _build_store_with_facility(tmp_path, make_rec)
    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir), public=True)

    facilities = json.loads((out_dir / "facilities.json").read_text(encoding="utf-8"))
    row = facilities["rows"][0]
    assert row["name"] is None
    assert row["district"] is None
    assert row["region"] is None
    assert row["status"] == "operational"  # non-identifying fields survive

    gha = json.loads((out_dir / "countries" / "GHA.json").read_text(encoding="utf-8"))
    assert gha["facilities"][0]["name"] is None
    assert facilities["manifest"]["public"] is True


def _add_query(db_path, query_id, scope, severity, indicator, status="open"):
    con = connect(db_path)
    con.execute("INSERT INTO fact_query(query_id,scope,severity,indicator,issue,status,source)"
                " VALUES (?,?,?,?,?,?,?)",
                (query_id, scope, severity, indicator, "test issue", status, "evidence review"))
    con.commit()
    con.close()


def test_queries_scoped_by_country_including_multi_country_scope(tmp_path, make_rec):
    db_path = _build_store(tmp_path, make_rec)
    _add_query(db_path, "Q-GHA-01", "GHA", "Medium", "2.3")
    _add_query(db_path, "Q-NOD-01", "LSO; NER; ZMB", "Low", "all")
    _add_query(db_path, "Q-OLD-01", "GHA", "Low", "2.3", status="closed")
    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir))

    quality = json.loads((out_dir / "quality.json").read_text(encoding="utf-8"))
    assert quality["kpis"]["open_queries"]["total"] == 2
    assert quality["kpis"]["queries_closed"] == 1
    gha_row = next(r for r in quality["provenance"] if r["iso3"] == "GHA")
    assert gha_row["open_queries"] == 1
    assert gha_row["highest_severity"] == "Medium"

    gha = json.loads((out_dir / "countries" / "GHA.json").read_text(encoding="utf-8"))
    assert {q["query_id"] for q in gha["queries"]} == {"Q-GHA-01", "Q-OLD-01"}
    ner = json.loads((out_dir / "countries" / "NER.json").read_text(encoding="utf-8"))
    assert [q["query_id"] for q in ner["queries"]] == ["Q-NOD-01"]
    ken = json.loads((out_dir / "countries" / "KEN.json").read_text(encoding="utf-8"))
    assert ken["queries"] == []


def test_all_31_countries_appear_in_provenance_and_coverage(tmp_path, make_rec):
    db_path = _build_store(tmp_path, make_rec)
    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir))
    quality = json.loads((out_dir / "quality.json").read_text(encoding="utf-8"))
    assert len(quality["provenance"]) == 31
    assert len(quality["coverage"]["rows"]) == 31
    assert quality["coverage"]["rows"][0]["cells"].keys() == set(export.CORE_INDICATORS)
    statuses = {r["iso3"]: r["status"] for r in quality["provenance"]}
    assert statuses["GHA"] == "validated"        # a form return in this fixture
    assert statuses["AGO"] == "no_return"        # never omitted, never "accepted"


def test_open_high_query_holds_the_figure_and_keeps_it_out_of_the_total(tmp_path, make_rec):
    db_path = str(tmp_path / "store.db")
    con = init_db(db_path)
    load_return(con, make_rec(country_name="Ghana", period_id="2026-Q1", quarter_id="2026-Q1"),
                verdict="accepted")
    load_return(con, make_rec(country_name="Kenya", period_id="2026-Q1", quarter_id="2026-Q1"),
                verdict="accepted")
    con.close()
    _add_query(db_path, "Q-KEN-99", "KEN", "High", "2.5")
    transform.build(db_path)
    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir))

    ind = json.loads((out_dir / "indicators.json").read_text(encoding="utf-8"))
    dim = next(d for d in ind["dim"] if d["indicator_code"] == "2.6")
    ken = next(v for v in ind["values"] if v["iso3"] == "KEN" and v["indicator_code"] == "2.6"
               and v["disagg_key"] == "all")
    gha = next(v for v in ind["values"] if v["iso3"] == "GHA" and v["indicator_code"] == "2.6"
               and v["disagg_key"] == "all")
    assert ken["held"] == 1 and ken["held_by"] == "Q-KEN-99"
    assert dim["regional_value"] == gha["numerator"]      # Kenya's held figure is not added
    assert dim["countries_reporting"] == 1
    assert dim["countries_held"] == 1


def test_regional_high_query_holds_the_regional_figure(tmp_path, make_rec):
    db_path = _build_store(tmp_path, make_rec)
    _add_query(db_path, "Q-REG-01", "REG", "High", "2.5")
    transform.build(db_path)
    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir))
    overview = json.loads((out_dir / "overview.json").read_text(encoding="utf-8"))
    assert overview["headline"]["sentinel_ever"]["total"] is None
    assert overview["headline"]["sentinel_ever"]["total_held_by"] == "Q-REG-01"
    # the country figures behind it are still published
    assert overview["headline"]["sentinel_ever"]["countries_reporting"] == 1


def test_implementation_json_without_phase_evidence_has_no_phase(tmp_path, make_rec):
    db_path = _build_store(tmp_path, make_rec)
    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir))

    impl = json.loads((out_dir / "implementation.json").read_text(encoding="utf-8"))
    assert len(impl["steps"]) == 14
    assert len(impl["countries"]) == 31
    gha = next(c for c in impl["countries"] if c["iso3"] == "GHA")
    assert len(gha["steps"]) == 14
    # No phase evidence: no phase -- never "not started" (phase 0).
    assert all(s["status"] is None for s in gha["steps"])
    assert gha["phase"] is None
    assert impl["no_return"] == 31


def test_phase_is_published_from_the_reconciliation_with_disagreements_flagged(tmp_path, make_rec):
    db_path = _build_store(tmp_path, make_rec)
    csv_path = tmp_path / "phases.csv"
    steps = ",".join(f"step_{i}" for i in range(1, 15))
    csv_path.write_text(
        f"country,{steps},workbook_phase,icppa_map_phase,phase_to_publish,agreement,note\n"
        "Ghana," + ",".join(["Y"] * 8 + ["N"] * 6) + ",3,4,4,NO,Map is more recent\n"
        "Rwanda," + ",".join(["Y"] * 14) + ",5,5,5,yes,\n"
        "Angola," + "," * 13 + ",,,,,Second HCT round: no return yet.\n",
        encoding="utf-8")
    con = connect(db_path)
    baseline.load_phase_reconciliation(con, str(csv_path))
    con.close()
    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir))

    impl = json.loads((out_dir / "implementation.json").read_text(encoding="utf-8"))
    by = {c["iso3"]: c for c in impl["countries"]}
    assert by["GHA"]["phase"] == 4 and by["GHA"]["workbook_phase"] == 3
    assert by["GHA"]["agreement"] == "no"
    assert by["GHA"]["steps"][8]["status"] == "no"        # step 9 as the workbook has it
    assert by["RWA"]["phase"] == 5
    assert by["AGO"]["phase"] is None
    assert impl["disagreements"] == 1
    assert {p["phase"]: p["countries"] for p in impl["phase_counts"]}[4] == 1
