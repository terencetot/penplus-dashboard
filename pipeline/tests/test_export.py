"""export.export() writes the static JSON bundle. Uses real temp files for the
same reason as test_transform.py: transform.build()/export.export() each open
their own connection to db_path, so ":memory:" would not share data."""
from __future__ import annotations

import json

import export
import transform
from load import init_db, load_implementation_steps, load_return
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


def test_public_export_withholds_facility_identity(tmp_path, make_rec):
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
                  if v["indicator_code"] == "2.5" and v["disagg_key"] == "condition"
                  and v["disagg_value"] == "t1d")
    assert row_25["suppressed"] == 1
    assert row_25["numerator"] is None  # withheld, not just flagged

    dim = next(d for d in indicators["dim"] if d["indicator_code"] == "2.5")
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


def test_open_queries_scoped_by_country(tmp_path, make_rec):
    db_path = _build_store(tmp_path, make_rec)
    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir))

    quality = json.loads((out_dir / "quality.json").read_text(encoding="utf-8"))
    assert len(quality["open_queries"]) == 1
    assert quality["open_queries"][0]["iso3"] == "GHA"
    gha_row = next(r for r in quality["rows"] if r["iso3"] == "GHA")
    assert gha_row["open_queries"] == 1

    gha = json.loads((out_dir / "countries" / "GHA.json").read_text(encoding="utf-8"))
    assert len(gha["open_queries"]) == 1
    assert gha["open_queries"][0]["section"] == "2.1"

    # a country with no findings gets an empty, correctly-scoped list
    ken = json.loads((out_dir / "countries" / "KEN.json").read_text(encoding="utf-8"))
    assert ken["open_queries"] == []


def test_implementation_json_has_all_31_countries_and_14_steps(tmp_path, make_rec):
    db_path = _build_store(tmp_path, make_rec)
    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir))

    impl = json.loads((out_dir / "implementation.json").read_text(encoding="utf-8"))
    assert len(impl["steps"]) == 14
    assert len(impl["countries"]) == 31
    gha = next(c for c in impl["countries"] if c["iso3"] == "GHA")
    assert len(gha["steps"]) == 14
    # no implementation-phase evidence loaded in this fixture: every step is
    # unreported, and the highest phase completed is 0 -- not fabricated.
    assert all(s["status"] is None for s in gha["steps"])
    assert gha["highest_phase_completed"] == 0


def test_highest_phase_completed_requires_every_step_of_the_phase(tmp_path, make_rec):
    db_path = str(tmp_path / "store.db")
    con = init_db(db_path)
    load_return(con, make_rec(country_name="Ghana", period_id="2026-Q1", quarter_id="2026-Q1"),
                verdict="accepted")
    # Phase 1 = steps 1-3, all yes: phase 1 complete.
    # Phase 2 = steps 4-6, step 5 not yes: phase 2 incomplete, so despite
    # step 7 (phase 3) being 'yes', the highest phase completed stays 1 --
    # phases are sequential, a later one does not count while an earlier one
    # is still open.
    load_implementation_steps(con, "GHA", {
        1: "yes", 2: "yes", 3: "yes",
        4: "yes", 5: "under_development", 6: "yes",
        7: "yes",
    }, source="test fixture", as_of="2026-01-01")
    con.close()
    transform.build(db_path)

    out_dir = tmp_path / "site_data"
    export.export(db_path, str(out_dir))
    impl = json.loads((out_dir / "implementation.json").read_text(encoding="utf-8"))
    gha = next(c for c in impl["countries"] if c["iso3"] == "GHA")
    assert gha["highest_phase_completed"] == 1
    step1 = next(s for s in gha["steps"] if s["step_no"] == 1)
    assert step1["status"] == "yes"
    assert step1["source"] == "test fixture"

    gha_country = json.loads((out_dir / "countries" / "GHA.json").read_text(encoding="utf-8"))
    assert gha_country["implementation"]["highest_phase_completed"] == 1
