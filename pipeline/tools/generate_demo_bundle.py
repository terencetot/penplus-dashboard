#!/usr/bin/env python3
"""
generate_demo_bundle.py - a synthetic, fully-populated bundle for design review.

Every number this script produces is invented. It exists so the site can be
evaluated fully populated -- most real cells are NR because no Phase Two
country has submitted a real return yet, which is honest but makes the
dashboard hard to judge visually. This script is not part of the pipeline
proper: it never touches penplus.db or site/public/data, and its own output
is written to a completely separate store and bundle
(demo.db, site/public/demo-data/) that the site only loads when a viewer
explicitly turns on demo mode, with a permanent on-screen banner while it is
on. Do not point run.py or seed_history.py at this script's output, and
never copy a number from it into a real fixture.

It still goes through the real pipeline (load_return, transform.build,
export.export unchanged) rather than hand-writing gold_indicator, so the
demo bundle obeys the exact same arithmetic, null discipline and
suppression rules as a real one -- the point is to review the design against
realistic volumes, not against numbers that could never occur.

    python3 generate_demo_bundle.py
"""
from __future__ import annotations

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src", "penplus_pipeline")
sys.path.insert(0, SRC)

import export  # noqa: E402
import transform  # noqa: E402
from common import COUNTRIES, IMPLEMENTATION_STEPS, TRACERS  # noqa: E402
from load import init_db, load_implementation_steps, load_return  # noqa: E402

DEMO_DB = os.path.join(SRC, "demo.db")
DEMO_OUT = os.path.join(HERE, "..", "..", "site", "public", "demo-data")
PROVENANCE = "SYNTHETIC DEMONSTRATION DATA -- invented for design review, not a real PEN-Plus report"

# Matches PHASE_BREAK_PERIOD in site/src/screens/indicator-detail.ts and
# country-profile.ts: the first Phase Two reporting period. A demo return
# from this period on is a (synthetic) form submission, not reconstructed
# history -- tagging it 'historical' would show a live-looking period as
# pre-programme evidence and hide it from any "Phase Two so far" framing.
PHASE_BREAK_PERIOD = "2026-Q1"

CADRES = ["doctors", "clinical_officers", "nurses_midwives", "pharmacy_lab", "other"]
PHASE1_PERIODS = ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1"]
PHASE2_PERIODS = ["2026-Q1"]  # Phase Two countries only start reporting once Phase Two begins
DAYS = {"2025-Q1": 90, "2025-Q2": 91, "2025-Q3": 92, "2025-Q4": 92, "2026-Q1": 90}
CLOSING = {"2025-Q1": "2025-03-31", "2025-Q2": "2025-06-30", "2025-Q3": "2025-09-30",
           "2025-Q4": "2025-12-31", "2026-Q1": "2026-03-31"}

DISTRICTS = ["Central", "Northern", "Southern", "Eastern", "Western", "Coastal", "Highlands"]
LEVELS = ["District hospital", "Regional hospital", "Referral hospital", "Health centre"]
GUIDELINE_TITLE = "{cond}_protocol_v2.pdf"

rng = random.Random(20260321)


def _facility_name(iso3, i):
    return f"{DISTRICTS[i % len(DISTRICTS)]} {LEVELS[i % len(LEVELS)]} {i + 1}"


def _grow(prev, lo, hi):
    return prev + rng.randint(lo, hi)


def build_country_series(iso3, name, cohort, periods, n_facilities):
    """One rec per period for one country, cumulative counts growing period over period."""
    ever = {c: rng.randint(20, 80) for c in TRACERS}
    facility_ids = [f"{iso3}-{i + 1:04d}" for i in range(n_facilities)]
    facility_names = [_facility_name(iso3, i) for i in range(n_facilities)]
    # facilities "mature" over time: more become operational in later periods
    recs = []
    for p_index, period in enumerate(periods):
        for c in TRACERS:
            ever[c] = _grow(ever[c], 3, 15)
        active = {c: max(0, ever[c] - rng.randint(5, 25)) for c in TRACERS}
        completeness_pct = rng.choice([100, 100, 90, 85, 70, 60])  # mostly good, sometimes low
        expected = n_facilities
        complete = round(expected * completeness_pct / 100)
        on_time = max(0, complete - rng.randint(0, 2))

        maturity = (p_index + 1) / len(periods)
        statuses = []
        for i in range(n_facilities):
            if i < n_facilities * maturity * 0.8:
                statuses.append("operational")
            elif i < n_facilities * maturity:
                statuses.append("started_this_period")
            else:
                statuses.append("under_preparation")
        if n_facilities > 6 and rng.random() < 0.15:
            statuses[-1] = "suspended"

        rec = {
            "source_file": f"{iso3}_{period}_PENPLUS_demo.docx",
            "checksum": f"demo-{iso3}-{period}",
            "country_name": name,
            "rhythm": "quarterly",
            "period_id": period,
            "quarter_id": period,
            "year": int(period[:4]),
            "closing_date": CLOSING[period],
            "first_return": "yes" if p_index == 0 else "no",
            "context": {
                "districts_total": rng.randint(15, 60),
                "first_referral_total": rng.randint(10, 40),
                "districts_with_penplus": max(1, round(n_facilities / 2)),
            },
            "quality": {
                "facilities_expected": expected,
                "returns_complete": complete,
                "returns_partial": max(0, expected - complete - 1) if expected > complete else 0,
                "returns_none": max(0, expected - complete - max(0, expected - complete - 1)),
                "returns_on_time": on_time,
            },
            "governance": [
                {"milestone_code": "1.1", "milestone": "PEN-Plus integrated into the national NCD strategy and UHC agenda",
                 "status": "yes" if maturity > 0.4 else "under_development",
                 "achieved_in": period if maturity > 0.4 else None,
                 "document": "ncd_strategy_addendum.pdf" if maturity > 0.4 else None},
                {"milestone_code": "1.2", "milestone": "PEN-Plus Plan developed, approved, launched and under implementation",
                 "status": "yes" if maturity > 0.7 else "under_development",
                 "achieved_in": period if maturity > 0.7 else None,
                 "document": "penplus_plan_signed.pdf" if maturity > 0.7 else None},
                {"milestone_code": "1.3", "milestone": "Costed National Operational Plan (NOP) on PEN-Plus developed and launched",
                 "status": "yes" if maturity > 0.9 else "no",
                 "achieved_in": period if maturity > 0.9 else None,
                 "document": "nop_costed_final.pdf" if maturity > 0.9 else None},
            ],
            "patient_stock": [
                {"condition": c, "ever_enrolled": ever[c], "active_end": active[c]} for c in TRACERS
            ],
            "patient_flow": [
                {"condition": c, "new_enrolled": rng.randint(3, 15), "ltfu": rng.randint(0, 4),
                 "transferred_out": rng.randint(0, 3), "died": rng.randint(0, 2),
                 "stopped": rng.randint(0, 2)}
                for c in TRACERS
            ],
            "retention": [
                {"condition": c, "numerator": round(active[c] * rng.uniform(0.7, 0.95)),
                 "denominator": active[c]}
                for c in TRACERS if period == periods[-1] and rng.random() > 0.1
            ],
            "ltfu_compliant": 1 if rng.random() > 0.15 else 0,
            "ltfu_rule": "Regional 90-day rule",
            "dedup_basis": "Facility register cross-checked monthly",
            "workforce_tot": [
                {"cadre": cadre, "trained_f": rng.randint(1, 6), "trained_m": rng.randint(1, 6),
                 "trained_ns": rng.randint(0, 1)}
                for cadre in CADRES
            ],
            "workforce": [
                {"cadre": cadre, "trained_f": rng.randint(0, 4), "trained_m": rng.randint(0, 4),
                 "trained_ns": rng.randint(0, 1), "fully_trained": None, "working_at_site": None}
                for cadre in CADRES
            ],
            "supply": [
                {"item": item, "availability": rng.choice(
                    ["always", "always", "sometimes", "never", "not_applicable"]),
                 "facilities_stockout": rng.randint(0, max(1, n_facilities // 3))}
                for item in ["Insulin", "Insulin syringes, pens or needles", "Blood glucose test strips",
                             "Hydroxyurea", "Benzathine benzylpenicillin",
                             "Sickle cell rapid or confirmatory tests", "HbA1c testing",
                             "Echocardiography or ultrasound access"]
            ],
            "confidence": {
                "facilities_and_coverage": rng.choice(["high", "high", "medium"]),
                "patients": rng.choice(["high", "medium", "medium", "low"]),
                "workforce": rng.choice(["high", "medium"]),
                "quality_and_mentorship": rng.choice(["medium", "low", "high"]),
                "governance_financing_hmis": rng.choice(["high", "medium"]),
            },
            "facilities": [],
            "facility_period": [],
        }
        for c in TRACERS:
            rec["context"][f"guideline_disseminated_{c}"] = 1 if maturity > rng.uniform(0.2, 0.8) else 0
        rec["context"]["who_academy_f"] = rng.randint(2, 10)
        rec["context"]["who_academy_m"] = rng.randint(2, 10)
        rec["context"]["who_academy_ns"] = rng.randint(0, 2)
        rec["context"]["round_table_held"] = 1 if (p_index == len(periods) - 1 and rng.random() > 0.3) else 0
        rec["context"]["budget_line_exists"] = 1 if maturity > 0.6 else 0
        rec["context"]["his_integration_level"] = 2 if maturity > 0.8 else (1 if maturity > 0.4 else 0)
        rec["context"]["comm_products_total"] = rng.randint(1, 8)
        rec["context"]["comm_consent_confirmed"] = 1

        for i, (fid, fname) in enumerate(zip(facility_ids, facility_names, strict=True)):
            status = statuses[i]
            if p_index == 0:
                rec["facilities"].append({
                    "facility_id": fid, "name": fname,
                    "region": DISTRICTS[i % len(DISTRICTS)] + " Region",
                    "district": DISTRICTS[i % len(DISTRICTS)] + " District",
                    "facility_type": LEVELS[i % len(LEVELS)],
                    "services_started": CLOSING[periods[0]],
                    "status": status,
                    "project_supported": rng.choice(["yes", "yes", "no", "partial"]),
                    "conditions": ",".join(rng.sample(TRACERS, k=rng.randint(1, 4))),
                })
            else:
                rec["facilities"].append({
                    "facility_id": fid, "name": fname, "status": status,
                    "region": None, "district": None, "facility_type": None,
                    "services_started": None,
                    "project_supported": rng.choice(["yes", "no", "partial"]),
                    "conditions": None,
                })
            if status in ("operational", "started_this_period"):
                fac_ever = max(1, round(ever[TRACERS[i % len(TRACERS)]] / n_facilities))
                fac_active = max(0, round(active[TRACERS[i % len(TRACERS)]] / n_facilities))
                assessed = rng.random() > 0.25
                rec["facility_period"].append({
                    "facility_id": fid, "name": fname,
                    "return_received": "yes" if rng.random() > 0.1 else "partial",
                    "ever_enrolled": fac_ever, "active_end": fac_active,
                    "mentorship_visit": 1 if rng.random() > 0.35 else 0,
                    "quality_score": rng.randint(55, 98) if assessed else None,
                    "critical_met": ("yes" if rng.random() > 0.3 else "no") if assessed else None,
                    "readiness_class": rng.choice(["green", "amber", "red"]) if assessed else "not_assessed",
                })
        recs.append(rec)
    return recs


def _synthetic_phase_progress(rng: random.Random) -> dict[int, str]:
    """A plausible per-country implementation-phase state: every step before
    a randomly chosen "current" phase is done, the current phase is a mix of
    done/in-progress/not-yet, and everything after it is left unset (so it
    reports as not_reported, not invented as a status). One in six countries
    reports nothing at all, matching the real programme's uneven reporting.
    """
    if rng.random() < 1 / 6:
        return {}
    phases_by_no: dict[int, list[int]] = {}
    for step_no, phase_no, _, _ in IMPLEMENTATION_STEPS:
        phases_by_no.setdefault(phase_no, []).append(step_no)
    current_phase = rng.choices([1, 2, 3, 4, 5], weights=[10, 20, 25, 30, 15])[0]
    steps: dict[int, str] = {}
    for phase_no, step_nos in phases_by_no.items():
        if phase_no < current_phase:
            for s in step_nos:
                steps[s] = "yes"
        elif phase_no == current_phase:
            for s in step_nos:
                steps[s] = rng.choices(
                    ["yes", "under_development", "no"], weights=[55, 35, 10])[0]
        # phase_no > current_phase: left out entirely (not_reported)
    return steps


def main():
    if os.path.exists(DEMO_DB):
        os.remove(DEMO_DB)
    con = init_db(DEMO_DB)

    # common.py's COUNTRIES carries alias entries for the parser's benefit
    # (e.g. "The Gambia" and "Gambia" both resolve to GMB) -- iterating the
    # dict as-is double-loads those three countries, which then supersede
    # their own first revision and silently swallow anything set on it
    # (this is how a hold-verdict/high-severity query aimed at one return
    # landed on a revision that got immediately superseded). One entry per
    # ISO3, first occurrence (the canonical, non-abbreviated name) kept.
    by_iso3: dict[str, tuple[str, str]] = {}
    for name, (iso3, cohort) in COUNTRIES.items():
        by_iso3.setdefault(iso3, (name, cohort))
    for iso3, (name, cohort) in sorted(by_iso3.items()):
        if cohort == "phase_1":
            periods, n_fac = PHASE1_PERIODS, rng.randint(6, 16)
        else:
            periods, n_fac = PHASE2_PERIODS, rng.randint(3, 8)
        for rec in build_country_series(iso3, name, cohort, periods, n_fac):
            source_kind = "form" if rec["period_id"] >= PHASE_BREAK_PERIOD else "historical"
            load_return(con, rec, source_kind=source_kind, provenance=PROVENANCE)

        # Implementation-phase status: round 1 (phase_1) evidence only.
        # Round 2 countries joined in June 2026 and the round 2 form carries
        # no implementation-phase question yet (docs/architecture.md,
        # "Implementation phases") -- they correctly show "not yet reported"
        # here too, exactly as the real bundle would, rather than inventing
        # progress the programme has no evidence for.
        if cohort == "phase_1":
            steps = _synthetic_phase_progress(rng)
            if steps:
                load_implementation_steps(con, iso3, steps,
                                          source="PEN_PLUS_MONITORING.xlsx (synthetic demo copy)",
                                          as_of="2026-06-30")

    # Milestones for the demo only: common.py's real registry stays null
    # (no real target has been published -- see docs/architecture.md). These
    # are set directly on the demo store so the milestone strip and
    # gap-to-milestone panels have something to draw against.
    demo_milestones = {
        "2.3": 120, "2.5": 25000, "2.6": 18000, "3.3": 4000, "2.4": None,
        "2.1": None, "2.2": 150, "3.1": 3000, "3.2": 1200, "3.4": None,
        "4.1": None, "5.1": None, "6.1": 200, "1.1": None, "1.2": None, "1.3": None,
    }
    for code, target in demo_milestones.items():
        if target is not None:
            con.execute("UPDATE dim_indicator SET milestone=? WHERE indicator_code=?",
                        (float(target), code))
    con.commit()

    # A handful of open queries, so the data-quality screen has something to
    # show. At least one is High severity and puts its return on hold, so the
    # tracker/quality screens exercise all four verdict-derived states
    # (accepted, query, hold) rather than only ever showing "accepted".
    sample_returns = [r["return_id"] for r in con.execute(
        "SELECT return_id FROM fact_return WHERE superseded=0 ORDER BY RANDOM() LIMIT 6")]
    severities = ["High"] + [rng.choice(["High", "Medium", "Low"]) for _ in sample_returns[1:]]
    for rid, sev in zip(sample_returns, severities, strict=True):
        con.execute(
            "INSERT INTO query_register(return_id,severity,section,field,observed,expected,"
            "question,status,raised_at) VALUES (?,?,?,?,?,?,?,'open',?)",
            (rid, sev, "2.6", "Retention denominator",
             "reported lower than the prior quarter", "a stable or growing cohort",
             "Please confirm the retention denominator against the facility register.",
             "2026-02-15"))
    high_severity_return = sample_returns[0]
    con.execute("UPDATE fact_return SET verdict='hold' WHERE return_id=?", (high_severity_return,))
    con.commit()

    transform.build(DEMO_DB)
    export.export(DEMO_DB, DEMO_OUT)
    print(f"demo bundle written to {DEMO_OUT}")


if __name__ == "__main__":
    main()
