"""Shared fixtures. `src/penplus_pipeline` is on sys.path via pyproject's
pytest.ini_options, so modules import the same way run.py imports them
(`from load import ...`, not a package-qualified path)."""
from __future__ import annotations

import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))  # so tests can `import fixtures....`

from load import init_db  # noqa: E402


@pytest.fixture
def db():
    con = init_db(":memory:")
    yield con
    con.close()


def _base_rec() -> dict:
    """A clean Ghana Q1 return: every rule in validate.py passes on this record."""
    return {
        "source_file": "GHA_2026_Q1_PENPLUS.docx",
        "checksum": "testchecksum01",
        "country_name": "Ghana",
        "rhythm": "quarterly",
        "period_id": "2026-Q1",
        "quarter_id": "2026-Q1",
        "year": 2026,
        "closing_date": "2026-03-31",
        "days_in_period": 90,
        "me_officer": "Jane Doe",
        "npo": "John Smith",
        "focal_point": "Focal Person",
        "email": "test@example.org",
        "first_return": "no",
        "context": {
            "districts_total": 20, "first_referral_total": 15, "phc_total": 300,
            "districts_with_penplus": 10, "districts_trained_no_site": 2,
        },
        "quality": {
            "facilities_expected": 10, "returns_complete": 8,
            "returns_partial": 1, "returns_none": 1,
        },
        "patient_stock": [
            {"condition": "t1d", "ever_enrolled": 120, "active_end": 100},
            {"condition": "scd", "ever_enrolled": 80, "active_end": 70},
            {"condition": "rhd", "ever_enrolled": 40, "active_end": 35},
            {"condition": "severe_htn", "ever_enrolled": 200, "active_end": 180},
            {"condition": "other_reported", "ever_enrolled": None, "active_end": 15},
        ],
        "patient_flow": [
            {"condition": "t1d", "new_enrolled": 10, "ltfu": 2, "transferred_out": 1,
             "stopped": 0, "died": 1},
            {"condition": "scd", "new_enrolled": 5, "ltfu": 1, "transferred_out": 0,
             "stopped": 0, "died": 0},
            {"condition": "rhd", "new_enrolled": 3, "ltfu": 0, "transferred_out": 0,
             "stopped": 0, "died": 0},
            {"condition": "severe_htn", "new_enrolled": 15, "ltfu": 3, "transferred_out": 1,
             "stopped": 1, "died": 2},
        ],
        # t1d age bands sum to 100, matching active_end for t1d exactly.
        "patient_age": [
            {"condition": "t1d", "age_band": "u15", "patients": 30},
            {"condition": "t1d", "age_band": "15_29", "patients": 40},
            {"condition": "t1d", "age_band": "30plus", "patients": 30},
        ],
        "workforce": [
            {"cadre": "doctors", "trained_f": 2, "trained_m": 3,
             "fully_trained": 10, "working_at_site": 8},
            {"cadre": "nurses_midwives", "trained_f": 5, "trained_m": 1,
             "fully_trained": 20, "working_at_site": 18},
        ],
        "training_capacity": {"tots": 5, "master_trainers": 2, "training_centres": 1},
        "supply": [],
        "service": [],
        "assumptions": [],
        "governance": [],
        "retention": [{"condition": "t1d", "numerator": 80, "denominator": 100}],
        "facilities": [],
        "facility_period": [],
        "confidence": {},
        "ltfu_compliant": 1,
        "ltfu_rule": None,
        "dedup_basis": "facility register",
        "patient_source": "facility register",
        "other_conditions": None,
    }


@pytest.fixture
def make_rec():
    """Factory: make_rec() returns a fresh, valid rec dict; override any field."""
    def _make(**overrides):
        rec = copy.deepcopy(_base_rec())
        rec.update(overrides)
        return rec
    return _make
