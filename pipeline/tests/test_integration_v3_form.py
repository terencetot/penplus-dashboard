"""End-to-end: a synthetic return through parse -> load -> transform.

The unit tests exercise parse_return() and transform.build() separately
against hand-built dicts; this proves the two actually agree with each other
on field names and table shapes for a return that went through the real
parser -- exactly where the section-numbering and column-order fixes in
this build could have silently disagreed with each other. Uses a real temp
file, not ":memory:": transform.build() opens its own connection to db_path
(see test_transform.py).
"""
from __future__ import annotations

import transform
from fixtures.build_synthetic_return import build_synthetic_return
from load import connect, init_db, load_return
from parse import parse_return
from validate import record_findings, validate_return


def test_v3_form_end_to_end(tmp_path):
    docx_path = str(tmp_path / "GHA_2026_Q1_PENPLUS_synthetic.docx")
    build_synthetic_return(docx_path)
    rec = parse_return(docx_path)

    db_path = str(tmp_path / "store.db")
    con = init_db(db_path)
    verdict, findings = validate_return(con, rec)
    assert verdict == "accepted", [f"{f.severity}: {f.question}" for f in findings]
    rid = load_return(con, rec, source_kind="form", verdict=verdict)
    record_findings(con, rid, findings)
    con.close()

    transform.build(db_path)
    con = connect(db_path)
    gold = {(g["iso3"], g["indicator_code"], g["disagg_key"], g["disagg_value"]): g
            for g in con.execute("SELECT * FROM gold_indicator WHERE iso3='GHA'")}

    # Governance: 1.1 achieved with a document, 1.3 explicitly "no".
    assert gold[("GHA", "1.1", "all", "all")]["numerator"] == 1
    assert gold[("GHA", "1.3", "all", "all")]["numerator"] == 0

    # 2.1: one of three priority conditions marked disseminated (denominator
    # is the count actually answered, not a hard-coded four).
    assert gold[("GHA", "2.1", "all", "all")]["numerator"] == 1
    assert gold[("GHA", "2.1", "all", "all")]["denominator"] == 3

    # 2.5 / 2.6: from the corrected, separate ever-enrolled and active tables.
    assert gold[("GHA", "2.5", "all", "all")]["numerator"] == 150 + 45  # t1d + rhd; scd is NR
    assert gold[("GHA", "2.6", "all", "all")]["numerator"] == 140 + 60  # t1d + scd; rhd is "-"

    # 2.6b: retention, only reported for t1d, and the 90-day rule applied.
    assert gold[("GHA", "2.6b", "condition", "t1d")]["numerator"] == 80
    assert gold[("GHA", "2.6b", "condition", "t1d")]["denominator"] == 100

    # 3.1: WHO Academy completions summed across sex categories.
    assert gold[("GHA", "3.1", "all", "all")]["numerator"] == 6 + 4 + 0

    # 3.2 (cumulative ToT, from fact_workforce_tot) is distinct from 3.3
    # (this-quarter training, from fact_workforce) even though both are
    # keyed by the same cadres in the same return.
    assert gold[("GHA", "3.2", "all", "all")]["numerator"] == (2 + 3) + (1 + 1) + (4 + 2) + (1 + 0) + (0 + 1)
    # 3.3 has no not-stated column on the current form (unlike 3.2): just
    # female + male per cadre.
    assert gold[("GHA", "3.3", "all", "all")]["numerator"] == (3 + 4) + (2 + 2) + (6 + 3) + (1 + 1) + (0 + 1)

    # 3.4: Annex A no longer carries facility-level performance (mentorship,
    # quality, readiness) -- that moved to the new monthly facility return,
    # not yet wired into this pipeline -- so 3.4 has no source to compute
    # from this quarter and correctly does not appear at all, rather than
    # being fabricated from the facility register's identity columns alone.
    assert ("GHA", "3.4", "all", "all") not in gold

    # 4.1: round table held.
    assert gold[("GHA", "4.1", "all", "all")]["numerator"] == 1

    # 6.1: communication products, from the form's own TOTAL row.
    assert gold[("GHA", "6.1", "all", "all")]["numerator"] == 7
