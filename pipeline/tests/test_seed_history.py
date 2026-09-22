"""seed_history.py must never publish a closing_date in the future.

A prior build stamped `f"{year}-12-31"` on the current, still-incomplete
year, so the dashboard showed "As of Dec 31, 2026" while the year was still
in progress. See docs/architecture.md, "Data integrity".
"""
from __future__ import annotations

import datetime as dt

import openpyxl

from seed_history import _closing_date_for_year, _match_step_no, from_monitoring_phases


def test_fully_elapsed_year_keeps_31_december():
    assert _closing_date_for_year(2025) == "2025-12-31"


def test_current_incomplete_year_uses_today_not_31_december():
    today = dt.date.today()
    result = _closing_date_for_year(today.year)
    assert result == today.isoformat()
    assert result < f"{today.year}-12-31"


def test_never_returns_a_future_date():
    today = dt.date.today().isoformat()
    for year in (today[:4], int(today[:4]) + 1, int(today[:4]) + 5):
        assert _closing_date_for_year(int(year)) <= today


# ------------------------------------------ implementation-phase parsing
def test_match_step_no_reads_the_step_number_from_a_paraphrased_header():
    assert _match_step_no("Step 1 - Comprehensive assessment") == 1
    assert _match_step_no("STEP 14") == 14
    assert _match_step_no("Step14") == 14


def test_match_step_no_falls_back_to_the_wording_when_no_step_number_is_present():
    # No "Step N" token at all, but the wording matches step 2 (SWOT analysis).
    assert _match_step_no("SWOT analysis of the national programme") == 2


def test_match_step_no_returns_none_for_an_unrelated_header():
    assert _match_step_no("Country") is None
    assert _match_step_no("") is None


def _build_phases_workbook(path, extra_cell_on_row=None):
    """A synthetic 'PEN plus phases' sheet matching the brief's description:
    headers split across rows 7-8, country in the fourth column, and
    (optionally) one row with a trailing extra cell that would misalign a
    column-position-based reader but must not affect a label-based one."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "PEN plus phases"
    for r in range(1, 7):
        ws.cell(row=r, column=1, value=f"banner row {r}")
    ws.cell(row=7, column=4, value="Country")
    ws.cell(row=7, column=5, value="Step 1")
    ws.cell(row=7, column=6, value="Step 2")
    ws.cell(row=8, column=5, value="Conduct a comprehensive assessment")
    ws.cell(row=8, column=6, value="SWOT analysis")
    rows = [
        ("Ghana", "Yes", "Ongoing"),
        ("Kenya", "No", "Yes"),
    ]
    for i, (country, s1, s2) in enumerate(rows):
        r = 9 + i
        ws.cell(row=r, column=4, value=country)
        ws.cell(row=r, column=5, value=s1)
        ws.cell(row=r, column=6, value=s2)
        if extra_cell_on_row == r:
            ws.cell(row=r, column=1, value="an unrelated extra cell before the real columns")
    wb.save(path)


def test_from_monitoring_phases_maps_by_header_not_position(tmp_path):
    path = str(tmp_path / "monitoring.xlsx")
    _build_phases_workbook(path)
    out = from_monitoring_phases(path)
    assert out["GHA"] == {1: "yes", 2: "under_development"}
    assert out["KEN"] == {1: "no", 2: "yes"}


def test_from_monitoring_phases_ignores_a_country_not_in_the_programme(tmp_path):
    path = str(tmp_path / "monitoring.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "PEN plus phases"
    ws.cell(row=7, column=4, value="Country")
    ws.cell(row=7, column=5, value="Step 1")
    ws.cell(row=9, column=4, value="Atlantis")
    ws.cell(row=9, column=5, value="Yes")
    wb.save(path)
    assert from_monitoring_phases(path) == {}


def test_from_monitoring_phases_returns_empty_when_sheet_missing(tmp_path):
    path = str(tmp_path / "no_phases_sheet.xlsx")
    wb = openpyxl.Workbook()
    wb.active.title = "Something else entirely"
    wb.save(path)
    assert from_monitoring_phases(path) == {}
