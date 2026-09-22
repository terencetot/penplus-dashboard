"""run.py's --returns loop must refuse a filename that looks like a worked
example, demo, test or synthetic fixture unless --allow-synthetic is passed
-- a real "Zambia worked example" .docx was once loaded into the live store
as if it were a genuine return, and only an audit caught it (see
docs/architecture.md, "Data integrity"). This is the regression test for
that guard, not for the parser itself.
"""
from __future__ import annotations

import sys

import run
from fixtures.build_synthetic_return import build_synthetic_return


def _run(argv, capsys):
    old_argv = sys.argv
    sys.argv = ["run.py", *argv]
    try:
        run.main()
    finally:
        sys.argv = old_argv
    return capsys.readouterr().out


def test_refuses_worked_example_filename_by_default(tmp_path, capsys):
    db_path = str(tmp_path / "store.db")
    docx_path = str(tmp_path / "PEN-Plus_Country_Report_Zambia_worked_example.docx")
    build_synthetic_return(docx_path)

    out = _run(["--db", db_path, "--returns", docx_path], capsys)

    assert "REFUSED" in out
    from load import connect
    con = connect(db_path)
    n = con.execute("SELECT COUNT(*) n FROM fact_return").fetchone()["n"]
    assert n == 0


def test_allow_synthetic_flag_permits_it(tmp_path, capsys):
    db_path = str(tmp_path / "store.db")
    docx_path = str(tmp_path / "GHA_2026_Q1_PENPLUS_synthetic.docx")
    build_synthetic_return(docx_path)

    out = _run(["--db", db_path, "--returns", docx_path, "--allow-synthetic"], capsys)

    assert "REFUSED" not in out
    from load import connect
    con = connect(db_path)
    n = con.execute("SELECT COUNT(*) n FROM fact_return").fetchone()["n"]
    assert n == 1


def test_ordinary_filename_is_not_refused(tmp_path, capsys):
    db_path = str(tmp_path / "store.db")
    docx_path = str(tmp_path / "GHA_2026_Q1_PENPLUS.docx")
    build_synthetic_return(docx_path)

    out = _run(["--db", db_path, "--returns", docx_path], capsys)

    assert "REFUSED" not in out
    from load import connect
    con = connect(db_path)
    n = con.execute("SELECT COUNT(*) n FROM fact_return").fetchone()["n"]
    assert n == 1
