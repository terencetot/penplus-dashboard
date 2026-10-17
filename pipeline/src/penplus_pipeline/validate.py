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


# ======================================================================
# Store-level checks R01-R17 (docs/refinement/04_data_quality/
# DATA_QUALITY_SPEC.md, section 4.4). They run on every live return in the
# store -- form returns and the historical evidence alike -- and record, per
# rule and return, passed / failed / not testable. "Not testable" is the
# honest answer where the evidence lacks the fields a rule needs (most of the
# ICPPA baseline): it is never counted as a pass.
#
# Every failure becomes a query in fact_query (source "validate.py Rnn").
# A High failure holds what it concerns: a form return gets verdict 'hold';
# a historical return's figure is held through its open High query.
# ======================================================================

#: rule -> (severity, what is checked, indicator(s) a failure concerns)
RULES = {
    "R01": (HIGH, "Section 0: complete + partial + no return = facilities expected", "data"),
    "R02": (HIGH, "Annex A facilities with status Active = 2.3 active during period", "2.3"),
    "R03": (HIGH, "2.3 active is no more than 2.3 initiated (cumulative)", "2.3"),
    "R04": (HIGH, "2.6 per condition: newly enrolled and active are no more than ever enrolled",
            "2.6"),
    "R05": (HIGH, "2.6 sentinel total is no more than 2.5 (sentinel is a subset)", "2.5/2.6"),
    "R06": (HIGH, "Cumulative stocks (2.3 initiated, 2.5, 2.6 ever, 3.1, 3.2) never decrease"
                  " between consecutive returns", "2.5/2.6"),
    "R07": (MEDIUM, "3.3: female + male = total per cadre; year to date is at least this quarter",
            "3.3"),
    "R08": (MEDIUM, "3.4 numerator no more than denominator; denominator = 2.3 active", "3.4"),
    "R09": (MEDIUM, "2.4: meeting criteria <= assessed <= 2.3 initiated; printed % = computed %"
                    " (within 1 point)", "2.4"),
    "R10": (MEDIUM, "Tracer stock-out facility counts are no more than 2.3 active", "supply"),
    "R11": (MEDIUM, "Every Yes on 1.1, 1.2, 1.3, 2.1 and 4.1 carries a document title",
            "governance"),
    "R12": (LOW, "Year achieved within 2015-2029 and not after the reporting year", "governance"),
    "R13": (MEDIUM, "Consent safeguard answered Yes whenever a communication product is reported",
            "6.1"),
    "R14": (LOW, "2.5 change on the previous return: above +100% or any decrease is flagged",
            "2.5"),
    "R15": (MEDIUM, "Plausibility: T1D patients per active facility at most the ceiling"
                    " (default 300)", "2.6"),
    "R16": (LOW, "Timeliness: date completed no later than quarter end + 30 days", "data"),
    "R17": (MEDIUM, "Cross-source: a form value within 10% of the ICPPA historical value for"
                    " the same country and year", "2.6"),
}
T1D_PER_FACILITY_CEILING = 300


def _ctx(con, rid):
    return {c["measure"]: c["value"] for c in con.execute(
        "SELECT measure, value FROM fact_context WHERE return_id=?", (rid,))}


def _sentinel(con, rid):
    from common import SENTINEL_SUM
    rows = {s["condition"]: s for s in con.execute(
        "SELECT * FROM fact_patient_stock WHERE return_id=?", (rid,))}
    flow = {f["condition"]: f for f in con.execute(
        "SELECT * FROM fact_patient_flow WHERE return_id=?", (rid,))}
    return {c: (rows[c], flow.get(c)) for c in SENTINEL_SUM if c in rows}


def _sum_or_none(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


def run_checks(con) -> dict[str, int]:
    """Run R01-R17 on every live return. Returns {rule: failures}."""
    import datetime as dt

    con.execute("DELETE FROM fact_check")
    con.execute("DELETE FROM fact_query WHERE source LIKE 'validate.py%'")
    returns = list(con.execute(
        "SELECT r.*, p.closing_date, p.year FROM fact_return r JOIN dim_period p USING(period_id)"
        " WHERE r.superseded=0 ORDER BY r.iso3, r.period_id"))
    register_active = {r["iso3"]: r["n"] for r in con.execute(
        "SELECT iso3, COUNT(*) n FROM dim_facility WHERE status='operational' GROUP BY iso3")}
    failures: dict[str, int] = {k: 0 for k in RULES}
    out, queries = [], []
    prev_by_country: dict = {}

    for r in returns:
        rid, iso3, pid = r["return_id"], r["iso3"], r["period_id"]
        ctx = _ctx(con, rid)
        q = con.execute("SELECT * FROM fact_quality WHERE return_id=?", (rid,)).fetchone()
        sent = _sentinel(con, rid)
        results: dict[str, tuple[str, str | None]] = {}

        def res(rule, ok, detail=None, results=results):
            results[rule] = ("not_testable", None) if ok is None else \
                (("passed", None) if ok else ("failed", detail))

        # R01
        if q and None not in (q["facilities_expected"], q["returns_complete"],
                              q["returns_partial"], q["returns_none"]):
            total = q["returns_complete"] + q["returns_partial"] + q["returns_none"]
            res("R01", total == q["facilities_expected"],
                f"{total} returns accounted for, {q['facilities_expected']} expected")
        else:
            res("R01", None)
        # R02 / R03 (form returns: Annex A and the 2.3 aggregates)
        fac_active, fac_init = ctx.get("fac_active"), ctx.get("fac_initiated")
        annex_active = con.execute(
            "SELECT COUNT(*) n FROM dim_facility f WHERE f.iso3=? AND f.status='operational'"
            " AND f.first_seen=?", (iso3, pid)).fetchone()["n"] if r["source_kind"] == "form" else None
        res("R02", None if fac_active is None or not annex_active else annex_active == fac_active,
            f"Annex A lists {annex_active} active, 2.3 reports {fac_active}")
        res("R03", None if None in (fac_active, fac_init) else fac_active <= fac_init,
            f"{fac_active} active of {fac_init} initiated")
        # R04
        bad, testable = [], False
        for c, (s, f) in sent.items():
            ever, active = s["ever_enrolled"], s["active_end"]
            new = f["new_enrolled"] if f else None
            if ever is None or (active is None and new is None):
                continue
            testable = True
            if active is not None and active > ever:
                bad.append(f"{c}: active {active} > ever {ever}")
            if new is not None and new > ever:
                bad.append(f"{c}: new {new} > ever {ever}")
        res("R04", (not bad) if testable else None, "; ".join(bad))
        # R05
        sentinel_ever = _sum_or_none(s["ever_enrolled"] for s, _ in sent.values())
        all_ever = ctx.get("patients_all_ever")
        res("R05", None if None in (sentinel_ever, all_ever) else sentinel_ever <= all_ever,
            f"sentinel {sentinel_ever} > all PEN-Plus {all_ever}")
        # R06 (consecutive returns of the same source kind)
        prev = prev_by_country.get(iso3)
        if prev is not None and prev["source_kind"] == r["source_kind"]:
            p_sent = _sum_or_none(s["ever_enrolled"] for s, _ in _sentinel(con, prev["return_id"]).values())
            p_ctx = _ctx(con, prev["return_id"])
            pairs = [("2.6 ever", p_sent, sentinel_ever),
                     ("2.5", p_ctx.get("patients_all_ever"), all_ever),
                     ("2.3 initiated", p_ctx.get("fac_initiated"), fac_init)]
            pairs = [(n, a, b) for n, a, b in pairs if a is not None and b is not None]
            drops = [f"{n} {a} in {prev['period_id']} -> {b}" for n, a, b in pairs if b < a]
            res("R06", (not drops) if pairs else None, "; ".join(drops))
        else:
            res("R06", None)
        # R07
        wf = list(con.execute("SELECT * FROM fact_workforce WHERE return_id=?", (rid,)))
        checks = []
        for w in wf:
            if w["trained_total"] is not None and None not in (w["trained_f"], w["trained_m"]):
                checks.append((w["cadre"], w["trained_f"] + w["trained_m"] + (w["trained_ns"] or 0)
                               == w["trained_total"]))
            if w["trained_ytd"] is not None and w["trained_total"] is not None:
                checks.append((w["cadre"] + " ytd", w["trained_ytd"] >= w["trained_total"]))
        res("R07", all(ok for _, ok in checks) if checks else None,
            ", ".join(n for n, ok in checks if not ok))
        # R08
        mn, md = ctx.get("mentorship_num"), ctx.get("mentorship_den")
        res("R08", None if None in (mn, md) else
            (mn <= md and (fac_active is None or md == fac_active)),
            f"mentorship {mn} of {md}; 2.3 active {fac_active}")
        # R09
        qa, qm, qp = ctx.get("quality_assessed"), ctx.get("quality_met"), ctx.get("quality_pct_reported")
        if None not in (qa, qm):
            ok = qm <= qa and (fac_init is None or qa <= fac_init)
            if qp is not None and qa > 0:
                ok = ok and abs(round(qm / qa * 100) - qp) <= 1
            res("R09", ok, f"{qm} met of {qa} assessed (printed {qp}%), {fac_init} initiated")
        else:
            res("R09", None)
        # R10
        so = [s for s in con.execute("SELECT * FROM fact_supply WHERE return_id=?", (rid,))
              if s["facilities_stockout"] is not None]
        res("R10", None if not so or fac_active is None else
            all(s["facilities_stockout"] <= fac_active for s in so),
            ", ".join(f"{s['item']} {s['facilities_stockout']}" for s in so
                      if fac_active is not None and s["facilities_stockout"] > fac_active))
        # R11 / R12
        gov = list(con.execute("SELECT * FROM fact_governance WHERE return_id=?"
                               " AND (milestone_code IN ('1.1','1.2','1.3','4.1')"
                               " OR milestone_code LIKE '2.1-%')", (rid,)))
        yes = [g for g in gov if g["status"] == "yes"]
        res("R11", None if not yes else all(g["document"] for g in yes),
            ", ".join(g["milestone_code"] for g in yes if not g["document"]))
        years = [(g["milestone_code"], g["achieved_in"]) for g in gov if g["achieved_in"]]
        def _bad_year(y, ry=r["year"]):
            return not (str(y).isdigit() and 2015 <= int(y) <= 2029 and (ry is None or int(y) <= ry))
        res("R12", None if not years else not any(_bad_year(y) for _, y in years),
            ", ".join(f"{c} {y}" for c, y in years if _bad_year(y)))
        # R13
        comm, consent = ctx.get("comm_products_total"), ctx.get("comm_consent_confirmed")
        res("R13", None if comm is None else (comm == 0 or consent == 1),
            f"{comm} products reported, consent safeguard not answered Yes")
        # R14
        if prev is not None and prev["source_kind"] == r["source_kind"] == "form":
            a, b = _ctx(con, prev["return_id"]).get("patients_all_ever"), all_ever
            res("R14", None if None in (a, b) or a == 0 else (b >= a and b <= 2 * a),
                f"2.5 {a} -> {b}")
        else:
            res("R14", None)
        # R15
        t1d = sent.get("t1d")
        n_fac = fac_active if fac_active else register_active.get(iso3)
        t1d_ever = t1d[0]["ever_enrolled"] if t1d else None
        res("R15", None if not n_fac or t1d_ever is None else
            t1d_ever / n_fac <= T1D_PER_FACILITY_CEILING,
            f"{t1d_ever} T1D patients over {n_fac} active facilities")
        # R16
        if r["source_kind"] == "form" and r["date_completed"] and r["closing_date"]:
            try:
                due = dt.date.fromisoformat(r["closing_date"]) + dt.timedelta(days=30)
                done = dt.date.fromisoformat(r["date_completed"][:10])
                res("R16", done <= due, f"completed {done}, due {due}")
            except ValueError:
                res("R16", None)
        else:
            res("R16", None)
        # R17
        if r["source_kind"] == "form" and sentinel_ever is not None:
            hist = con.execute(
                "SELECT r.return_id FROM fact_return r WHERE r.iso3=? AND r.superseded=0"
                " AND r.source_kind='historical' AND r.period_id=?",
                (iso3, f"{r['year']}-A")).fetchone()
            h = _sum_or_none(s["ever_enrolled"] for s, _ in _sentinel(con, hist["return_id"]).values()) \
                if hist else None
            res("R17", None if not h else abs(sentinel_ever - h) / h <= 0.10,
                f"form {sentinel_ever} vs ICPPA {h}")
        else:
            res("R17", None)

        high_fail = False
        for rule, (outcome, detail) in results.items():
            out.append((rule, rid, iso3, pid, outcome, detail))
            if outcome == "failed":
                failures[rule] += 1
                sev, what, ind = RULES[rule]
                high_fail |= sev == HIGH
                queries.append((f"V-{rule}-{iso3}-{pid}", iso3, sev, ind,
                                f"{what}: {detail}", f"validate.py {rule}, {r['source_kind']} return",
                                "Ask the WCO to confirm or correct the figure.", "open", None,
                                f"validate.py {rule}", rule, pid, dt.date.today().isoformat()))
        if high_fail and r["source_kind"] == "form":
            con.execute("UPDATE fact_return SET verdict='hold' WHERE return_id=?", (rid,))
        prev_by_country[iso3] = r

    con.executemany("INSERT OR REPLACE INTO fact_check VALUES (?,?,?,?,?,?)", out)
    con.executemany(
        "INSERT OR REPLACE INTO fact_query(query_id,scope,severity,indicator,issue,evidence,action,"
        "status,resolution,source,rule,period_id,opened_on) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        queries)
    con.commit()
    return failures
