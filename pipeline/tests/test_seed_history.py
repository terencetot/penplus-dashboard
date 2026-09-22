"""seed_history.py must never publish a closing_date in the future.

A prior build stamped `f"{year}-12-31"` on the current, still-incomplete
year, so the dashboard showed "As of Dec 31, 2026" while the year was still
in progress. See docs/architecture.md, "Data integrity".
"""
from __future__ import annotations

import datetime as dt

from seed_history import _closing_date_for_year


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
