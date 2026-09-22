#!/usr/bin/env python3
"""
run.py - one command for the whole chain.

    python3 run.py --rebuild                      # seed history, transform, export
    python3 run.py --returns returns/*.docx       # add real country returns
    python3 run.py --transform --export           # recompute and republish

Seeding is idempotent in effect, not in mechanism: re-running creates new
revisions and supersedes the old ones, so history is never lost.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import export  # noqa: E402
import seed_history  # noqa: E402
import transform  # noqa: E402
from load import init_db, load_return  # noqa: E402
from parse import parse_return  # noqa: E402
from validate import record_findings, validate_return  # noqa: E402

# Historical seed workbooks are Regional M&E evidence, not part of this
# repository. Point --icppa/--monitoring at your own copies; --seed is a
# no-op (with a warning) when the files are not found at those paths.
RAW = os.path.join(HERE, "..", "..", "..", "data", "raw")
ICPPA = os.path.join(RAW, "PEN-Plus_country_data_ICPPA2026.xlsx")
MONITORING = os.path.join(RAW, "PEN_PLUS_MONITORING.xlsx")

# A worked example, demo or test fixture must never be loaded as a real
# country return -- that happened once (a "Zambia worked example" .docx
# ended up in the live store, source_kind='form') and was only caught by a
# later audit. See docs/architecture.md, "Data integrity".
SYNTHETIC_NAME_RE = re.compile(r"example|demo|\btest\b|synthetic", re.I)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=os.path.join(HERE, "penplus.db"))
    ap.add_argument("--fresh", action="store_true", help="delete the store first")
    ap.add_argument("--seed", action="store_true", help="load the historical evidence")
    ap.add_argument("--icppa", default=ICPPA)
    ap.add_argument("--monitoring", default=MONITORING)
    ap.add_argument("--returns", nargs="*", default=[], help="completed .docx returns")
    ap.add_argument("--allow-synthetic", action="store_true",
                     help="permit a --returns filename that looks like a worked example, "
                          "demo, test or synthetic fixture to be loaded as a real return")
    ap.add_argument("--transform", action="store_true")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "..", "site", "public", "data"))
    ap.add_argument("--public", action="store_true",
                     help="withhold facility identity and blank cells under 5, rather than "
                          "just flagging them -- use this for any export that reaches "
                          "site/public/data, since that directory ships to GitHub Pages "
                          "with no non-public audience")
    ap.add_argument("--rebuild", action="store_true", help="fresh, seed, transform, export")
    a = ap.parse_args()

    if a.rebuild:
        a.fresh = a.seed = a.transform = a.export = True
    if a.fresh and os.path.exists(a.db):
        os.remove(a.db)

    con = init_db(a.db)

    if a.seed:
        n = 0
        if os.path.exists(a.monitoring):
            for _country, rec in sorted(seed_history.from_monitoring(a.monitoring).items()):
                load_return(con, rec, source_kind="historical",
                            provenance=seed_history.PROV_MON)
                n += 1
        else:
            print(f"skipping monitoring seed: {a.monitoring} not found")
        if os.path.exists(a.icppa):
            for _key, rec in sorted(seed_history.from_icppa(a.icppa).items()):
                load_return(con, rec, source_kind="historical",
                            provenance=seed_history.PROV_ICPPA)
                n += 1
        else:
            print(f"skipping ICPPA seed: {a.icppa} not found")
        print(f"seeded {n} historical returns")

    paths = []
    for pat in a.returns:
        paths.extend(sorted(glob.glob(pat)) or [pat])
    for path in paths:
        name = os.path.basename(path)
        if SYNTHETIC_NAME_RE.search(name) and not a.allow_synthetic:
            print(f"REFUSED {name}: looks like a worked example, demo, test or synthetic "
                  "fixture -- pass --allow-synthetic to load it anyway")
            continue
        try:
            rec = parse_return(path)
        except Exception as exc:
            print(f"REJECTED {name}: {exc}")
            continue
        verdict, findings = validate_return(con, rec)
        rid = load_return(con, rec, source_kind="form", verdict=verdict)
        record_findings(con, rid, findings)
        if verdict == "hold":
            high = sum(1 for f in findings if f.severity == "High")
            print(f"HELD {name} as return {rid}: {high} high-severity finding(s), "
                  "excluded from gold_indicator until resolved")
        elif verdict == "query":
            print(f"loaded {name} as return {rid}, {len(findings)} finding(s) queried")
        else:
            print(f"loaded {name} as return {rid}, no findings")

    if a.transform:
        transform.build(a.db)
    if a.export:
        export.export(a.db, a.out, public=a.public)


if __name__ == "__main__":
    main()
