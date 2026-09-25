#!/usr/bin/env python3
"""
validate.py - the quality control gate between parse and load.

This is stage 3 of the pipeline described in the specification: "The quality
control rules run: arithmetic, cascade, longitudinal, plausibility" and produce
"a query register and a pass, hold or query verdict". Before this module
existed, every parsed return was loaded as `verdict='accepted'` regardless of
its content, which is inconsistent with acceptance criterion 2 of the
specification: "A return with a deliberate arithmetic error is held, appears in
the query register, and does not change any published figure."

A High severity finding holds the return: `transform.py` already excludes
`verdict='hold'` from `gold_indicator`, so a held return is queried but never
published. Medium and Low findings are queried but still loaded, so a small
gap in one field does not block a whole country's return.

    from validate import validate_return
    verdict, findings = validate_return(con, rec)

`findings` is a list of Finding, ready to write to `query_register` once
`load_return` has returned a `return_id`.
"""
from __future__ import annotations

from dataclasses import dataclass

from common import TRACERS, resolve_iso3

HIGH, MEDIUM, LOW = "High", "Medium", "Low"


@dataclass
class Finding:
    severity: str
    section: str
    field: str
    observed: str
    expected: str
    question: str


class Register:
    """Collects findings for one return. Mirrors the shape of query_register."""

    def __init__(self):
        self.findings: list[Finding] = []

    def add(self, severity, section, field, observed, expected, question):
        self.findings.append(Finding(severity, section, field, str(observed),
                                      str(expected), question))

    def high(self, *a):
        self.add(HIGH, *a)

    def medium(self, *a):
        self.add(MEDIUM, *a)

    def low(self, *a):
        self.add(LOW, *a)


# --------------------------------------------------------------------- rules
def _check_identification(rec, reg: Register):
    """A return with no country, period or closing date cannot be filed at all."""
    for field, label in (("country_name", "Country"), ("period_id", "Period reported"),
                          ("closing_date", "Closing date")):
        if not rec.get(field):
            reg.high("1", label, "empty", "a value",
                     f"'{label}' was left empty in Section 1. The return cannot be "
                     "filed against a country and period without it.")


def _check_patient_cascade(rec, reg: Register):
    """Active in care cannot exceed cumulative enrolment for the same condition."""
    stock = {r["condition"]: r for r in rec.get("patient_stock", [])}
    for cond in TRACERS:
        r = stock.get(cond)
        if not r:
            continue
        ever, active = r.get("ever_enrolled"), r.get("active_end")
        if ever is not None and active is not None and active > ever:
            reg.high("2.1", f"{cond} / active vs ever enrolled",
                     f"active_end={active}, ever_enrolled={ever}",
                     "active_end no greater than ever_enrolled",
                     f"For {cond}, more patients are reported active in care ({active}) than "
                     f"have ever been enrolled ({ever}). Please check both figures.")


def _check_age_reconciliation(rec, reg: Register):
    """The data model requires the age bands to sum to active_end for the condition."""
    stock = {r["condition"]: r for r in rec.get("patient_stock", [])}
    sums, counted = {}, {}
    for r in rec.get("patient_age", []):
        cond = r["condition"]
        if cond == "total" or r.get("patients") is None:
            continue
        sums[cond] = sums.get(cond, 0) + r["patients"]
        counted[cond] = True
    for cond, total in sums.items():
        active = stock.get(cond, {}).get("active_end")
        if active is not None and total != active:
            reg.high("2 (age table)", f"{cond} / age bands vs active in care",
                     f"age bands sum to {total}", f"active_end = {active}",
                     f"For {cond}, the age bands sum to {total} but active in care at period "
                     f"end is reported as {active}. Please reconcile the two.")


def _check_longitudinal(con, iso3, rec, reg: Register):
    """Ever enrolled is cumulative and must never decrease between periods."""
    for r in rec.get("patient_stock", []):
        cond, ever = r["condition"], r.get("ever_enrolled")
        if ever is None:
            continue
        prev = con.execute(
            "SELECT s.ever_enrolled, r.period_id FROM fact_patient_stock s"
            " JOIN fact_return r USING(return_id)"
            " WHERE r.iso3=? AND s.condition=? AND r.superseded=0"
            " AND r.verdict!='hold' AND r.period_id<? AND s.ever_enrolled IS NOT NULL"
            " ORDER BY r.period_id DESC LIMIT 1",
            (iso3, cond, rec["period_id"])).fetchone()
        if prev and ever < prev["ever_enrolled"]:
            reg.high("2.1", f"{cond} / ever enrolled",
                     f"{ever} this period, {prev['ever_enrolled']} in {prev['period_id']}",
                     "a cumulative figure that never decreases",
                     f"For {cond}, ever enrolled has fallen from {prev['ever_enrolled']} in "
                     f"{prev['period_id']} to {ever} this period. Ever enrolled is cumulative "
                     "and cannot decrease; please check for a transcription error or explain "
                     "the correction.")


def _check_plausible_growth(con, iso3, rec, reg: Register):
    """A cumulative figure that never decreases can still jump implausibly.

    The longitudinal check above catches a fall; this one catches a rise a
    reasonable reviewer would ask about before trusting it -- more than
    doubling in a single period is well outside how a facility caseload
    actually grows quarter to quarter. Medium, not High: an implausible jump
    still gets a second look from the focal point, but a genuine catch-up
    return (a country reporting for the first time in a year) is a real,
    if unusual, figure and should not be held back from the regional total
    the way a cascade or arithmetic error is.
    """
    for r in rec.get("patient_stock", []):
        cond, ever = r["condition"], r.get("ever_enrolled")
        if ever is None:
            continue
        prev = con.execute(
            "SELECT s.ever_enrolled, r.period_id FROM fact_patient_stock s"
            " JOIN fact_return r USING(return_id)"
            " WHERE r.iso3=? AND s.condition=? AND r.superseded=0"
            " AND r.verdict!='hold' AND r.period_id<? AND s.ever_enrolled IS NOT NULL"
            " ORDER BY r.period_id DESC LIMIT 1",
            (iso3, cond, rec["period_id"])).fetchone()
        if prev and prev["ever_enrolled"] > 0 and ever > prev["ever_enrolled"] * 2:
            reg.medium("2.1", f"{cond} / ever enrolled",
                       f"{ever} this period, {prev['ever_enrolled']} in {prev['period_id']}",
                       "growth in line with prior quarters",
                       f"For {cond}, ever enrolled more than doubled since {prev['period_id']} "
                       f"({prev['ever_enrolled']} to {ever}). Please confirm this is a real change "
                       "(e.g. a catch-up return, a new facility, deduplication fixed) rather than "
                       "a transcription error.")


def _check_completeness(rec, reg: Register):
    q = rec.get("quality") or {}
    exp, comp = q.get("facilities_expected"), q.get("returns_complete")
    if exp is not None and comp is not None and comp > exp:
        reg.high("1 (completeness)", "Complete returns vs facilities expected",
                 f"{comp} complete of {exp} expected", "complete returns no greater than expected",
                 f"{comp} facilities are reported as returning complete data, more than the "
                 f"{exp} expected. Please check both figures.")


def _check_retention(rec, reg: Register):
    for r in rec.get("retention", []):
        n, d = r.get("numerator"), r.get("denominator")
        if n is not None and d is not None and n > d:
            reg.high("6.2", f"Retention / {r['condition']}", f"{n} of {d}",
                     "numerator no greater than denominator",
                     f"For {r['condition']}, the retention numerator ({n}) exceeds the "
                     f"denominator ({d}). Please check both figures.")


def validate_return(con, rec) -> tuple[str, list[Finding]]:
    """Run every rule against a parsed return. Returns (verdict, findings).

    verdict is 'hold' if any finding is High severity, 'query' if there are
    findings but none High, otherwise 'accepted'.
    """
    reg = Register()
    _check_identification(rec, reg)
    if rec.get("country_name") and rec.get("period_id"):
        iso3 = resolve_iso3(rec["country_name"])
        _check_patient_cascade(rec, reg)
        _check_age_reconciliation(rec, reg)
        _check_longitudinal(con, iso3, rec, reg)
        _check_plausible_growth(con, iso3, rec, reg)
        _check_completeness(rec, reg)
        _check_retention(rec, reg)

    if any(f.severity == HIGH for f in reg.findings):
        verdict = "hold"
    elif reg.findings:
        verdict = "query"
    else:
        verdict = "accepted"
    return verdict, reg.findings


def record_findings(con, return_id: int, findings: list[Finding]) -> None:
    import datetime as dt
    con.executemany(
        "INSERT INTO query_register(return_id,severity,section,field,observed,expected,"
        "question,status,raised_at) VALUES (?,?,?,?,?,?,?,'open',?)",
        [(return_id, f.severity, f.section, f.field, f.observed, f.expected, f.question,
          dt.date.today().isoformat()) for f in findings])
    con.commit()
