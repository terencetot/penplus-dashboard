#!/usr/bin/env python3
"""
reconcile.py - old published figure vs new, per country, with the reason.

    python3 pipeline/tools/reconcile.py OLD_BUNDLE_DIR [NEW_BUNDLE_DIR]

OLD is a bundle built before refinement v2, where 2.5 meant "unique patients
ever enrolled" summed over T1D/SCD/RHD/severe HTN, 2.6 meant active in care,
3.3 trained. NEW is the rebuilt bundle (default: site/public/data), where
2.5 = all PEN-Plus patients, 2.6 = sentinel ever enrolled, 2.6a = sentinel
active. Prints a Markdown table and exits non-zero if an expected figure
from docs/refinement/00_START_HERE.md (stage 3) is not reproduced.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NEW_DEFAULT = os.path.join(HERE, "..", "..", "site", "public", "data")

#: Stage 3 expectations: (iso3, new code, disaggregation, value, held?)
EXPECTED = [
    ("UGA", "2.6", "all", 2226, False),
    ("BFA", "2.6", "all", 500, False),
    ("BFA", "2.6", "scd", 500, False),
    ("COD", "2.6", "all", 7, False),
    ("COD", "2.6", "scd", 7, False),
    ("ZWE", "2.6", "all", 4590, True),
    ("SLE", "2.6", "all", 1829, False),
    ("LBR", "2.6", "all", 90, False),
    ("KEN", "2.6", "all", 559, False),
    ("KEN", "2.6", "t1d", 310, False),
    ("TZA", "2.6a", "all", 558, False),
    ("ETH", "2.5", "all", 865, False),
    ("MOZ", "2.5", "all", 254, False),
    ("ZMB", "2.5", "all", 1397, False),
    ("ZMB", "2.6", "scd", 712, False),
    ("ZMB", "2.6", "t1d", 93, False),
]
EXPECTED_PHASES = {5: 1, 4: 15, 3: 3, 2: 1, None: 11}


def _load(d, name):
    with open(os.path.join(d, name), encoding="utf-8") as f:
        return json.load(f)


def latest(values, code, key="all", val="all"):
    out = {}
    for v in values:
        if v["indicator_code"] == code and v["disagg_key"] == key and v["disagg_value"] == val:
            if v["iso3"] not in out or v["period_id"] > out[v["iso3"]]["period_id"]:
                out[v["iso3"]] = v
    return out


def main():
    old_dir = sys.argv[1]
    new_dir = sys.argv[2] if len(sys.argv) > 2 else NEW_DEFAULT
    old = _load(old_dir, "indicators.json")["values"]
    new = _load(new_dir, "indicators.json")["values"]

    old_ever = latest(old, "2.5")
    old_active = latest(old, "2.6")
    old_trained = latest(old, "3.3")
    n25, n26, n26a = latest(new, "2.5"), latest(new, "2.6"), latest(new, "2.6a")
    n33 = latest(new, "3.3", "measure", "to_date")

    def fmt(v):
        if not v or v["value"] is None:
            return ""
        s = f"{v['value']:,.0f}"
        return s + (" (held)" if v.get("held") else "")

    def src(*vs):
        return "; ".join(sorted({v.get("source_ref") for v in vs if v and v.get("source_ref")}))

    print("| Country | Old 2.5 (priority ever) | New 2.6 sentinel ever | New 2.5 all conditions |"
          " Old 2.6 active | New 2.6a sentinel active | Old 3.3 | New 3.3 to date | Source |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    isos = sorted(set(old_ever) | set(n25) | set(n26) | set(n26a) | set(n33) | set(old_active))
    for iso in isos:
        row = [iso, fmt(old_ever.get(iso)), fmt(n26.get(iso)), fmt(n25.get(iso)),
               fmt(old_active.get(iso)), fmt(n26a.get(iso)), fmt(old_trained.get(iso)),
               fmt(n33.get(iso)), src(n26.get(iso), n25.get(iso), n26a.get(iso), n33.get(iso))]
        if any(row[1:8]):
            print("| " + " | ".join(row) + " |")

    failures = []
    for iso, code, val, want, held in EXPECTED:
        rows = latest(new, code, "all" if val == "all" else "condition", val)
        got = rows.get(iso)
        if not got or got["numerator"] != want or bool(got.get("held")) != held:
            failures.append(f"{iso} {code} {val}: expected {want}{' held' if held else ''},"
                            f" got {got and got['numerator']}{' held' if got and got.get('held') else ''}")
    impl = _load(new_dir, "implementation.json")["countries"]
    phases = {}
    for c in impl:
        phases[c.get("phase")] = phases.get(c.get("phase"), 0) + 1
    if phases != EXPECTED_PHASES:
        failures.append(f"phases: expected {EXPECTED_PHASES}, got {phases}")
    print()
    if failures:
        print("NOT REPRODUCED:")
        for f in failures:
            print("  - " + f)
        sys.exit(1)
    print(f"All {len(EXPECTED)} expected figures and the phase split reproduced.")


if __name__ == "__main__":
    main()
