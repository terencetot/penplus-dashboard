"""One test per rule in validate.py. Every rule implemented today is High
severity, so any single violation forces verdict == 'hold' (see the module
docstring: 'A High severity finding holds the return')."""
from __future__ import annotations

import pytest

from load import load_return
from validate import validate_return


def test_clean_record_is_accepted_with_no_findings(db, make_rec):
    verdict, findings = validate_return(db, make_rec())
    assert verdict == "accepted"
    assert findings == []


# ------------------------------------------------------------- identification
@pytest.mark.parametrize("field,label", [
    ("country_name", "Country"),
    ("period_id", "Period reported"),
    ("closing_date", "Closing date"),
])
def test_identification_missing_field_holds(db, make_rec, field, label):
    rec = make_rec(**{field: ""})
    verdict, findings = validate_return(db, rec)
    assert verdict == "hold"
    assert any(f.severity == "High" and f.section == "1" and f.field == label
               for f in findings)


# ------------------------------------------------------------- patient cascade
def test_patient_cascade_pass(db, make_rec):
    verdict, findings = validate_return(db, make_rec())
    assert verdict == "accepted"
    assert not any(f.section == "2.1" for f in findings)


def test_patient_cascade_violation_holds(db, make_rec):
    rec = make_rec()
    rec["patient_stock"][0]["active_end"] = 999  # t1d: ever_enrolled=120
    verdict, findings = validate_return(db, rec)
    assert verdict == "hold"
    f = next(f for f in findings if f.section == "2.1" and "t1d" in f.field)
    assert f.severity == "High"
    assert "active vs ever enrolled" in f.field


# --------------------------------------------------------- age reconciliation
def test_age_reconciliation_pass(db, make_rec):
    verdict, findings = validate_return(db, make_rec())
    assert verdict == "accepted"
    assert not any(f.section == "2 (age table)" for f in findings)


def test_age_reconciliation_violation_holds(db, make_rec):
    rec = make_rec()
    # t1d bands already sum to 100 (= active_end); add one more to break it.
    rec["patient_age"].append({"condition": "t1d", "age_band": "u15", "patients": 5})
    verdict, findings = validate_return(db, rec)
    assert verdict == "hold"
    f = next(f for f in findings if f.section == "2 (age table)")
    assert f.severity == "High"
    assert "t1d" in f.field


# ------------------------------------------------------------------ longitudinal
def test_longitudinal_pass_when_ever_enrolled_does_not_decrease(db, make_rec):
    rec1 = make_rec()
    load_return(db, rec1, verdict="accepted")

    rec2 = make_rec(period_id="2026-Q2", quarter_id="2026-Q2")
    verdict, findings = validate_return(db, rec2)
    assert verdict == "accepted"
    assert not any(f.section == "2.1" and "ever enrolled" in f.field for f in findings)


def test_longitudinal_violation_holds_when_ever_enrolled_falls(db, make_rec):
    rec1 = make_rec()
    load_return(db, rec1, verdict="accepted")

    rec2 = make_rec(period_id="2026-Q2", quarter_id="2026-Q2")
    # Isolate the longitudinal rule: keep the cascade (active<=ever) and the
    # age reconciliation (bands sum to active_end) both satisfied at the new,
    # lower level, so only the decrease itself is flagged.
    rec2["patient_stock"][0]["ever_enrolled"] = 50  # was 120 in rec1
    rec2["patient_stock"][0]["active_end"] = 40
    rec2["patient_age"] = [{"condition": "t1d", "age_band": "u15", "patients": 40}]

    verdict, findings = validate_return(db, rec2)
    assert verdict == "hold"
    f = next(f for f in findings if f.section == "2.1" and "ever enrolled" in f.field)
    assert f.severity == "High"
    assert "t1d" in f.field
    assert "120" in f.observed and "50" in f.observed


def test_longitudinal_ignores_held_prior_return(db, make_rec):
    """A superseded/held prior return must not anchor the longitudinal check."""
    rec1 = make_rec()
    load_return(db, rec1, verdict="hold")  # e.g. a bad first submission

    rec2 = make_rec(period_id="2026-Q2", quarter_id="2026-Q2")
    rec2["patient_stock"][0]["ever_enrolled"] = 1  # far below rec1, but rec1 was held
    rec2["patient_stock"][0]["active_end"] = 1
    rec2["patient_age"] = [{"condition": "t1d", "age_band": "u15", "patients": 1}]

    verdict, findings = validate_return(db, rec2)
    assert not any(f.section == "2.1" and "ever enrolled" in f.field for f in findings)
    assert verdict == "accepted"


# -------------------------------------------------------------- completeness
def test_completeness_pass(db, make_rec):
    verdict, findings = validate_return(db, make_rec())
    assert verdict == "accepted"
    assert not any(f.section == "1 (completeness)" for f in findings)


def test_completeness_violation_holds(db, make_rec):
    rec = make_rec()
    rec["quality"]["returns_complete"] = 999  # facilities_expected is 10
    verdict, findings = validate_return(db, rec)
    assert verdict == "hold"
    f = next(f for f in findings if f.section == "1 (completeness)")
    assert f.severity == "High"


# ----------------------------------------------------------------- retention
def test_retention_pass(db, make_rec):
    verdict, findings = validate_return(db, make_rec())
    assert verdict == "accepted"
    assert not any(f.section == "6.2" for f in findings)


def test_retention_violation_holds(db, make_rec):
    rec = make_rec()
    rec["retention"][0]["numerator"] = 999  # denominator is 100
    verdict, findings = validate_return(db, rec)
    assert verdict == "hold"
    f = next(f for f in findings if f.section == "6.2")
    assert f.severity == "High"
    assert "t1d" in f.field
