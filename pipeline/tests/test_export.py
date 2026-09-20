"""export.export() writes the static JSON bundle. Uses real temp files for the
same reason as test_transform.py: transform.build()/export.export() each open
their own connection to db_path, so ":memory:" would not share data."""
from __future__ import annotations

import json

import export
import transform
from load import init_db, load_return
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
