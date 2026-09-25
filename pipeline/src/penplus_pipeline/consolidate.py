#!/usr/bin/env python3
"""
consolidate.py - the two outputs a focal point needs after loading a batch
of returns: a partner-facing Excel workbook, and one data-quality report per
country.

This is the last stage of the process described in the specification: a
country return is parsed, validated and loaded (parse.py, validate.py,
load.py), transformed into gold_indicator (transform.py), and exported to
the dashboard's JSON bundle (export.py). Alongside that bundle, this module
produces:

1. A single consolidated .xlsx workbook -- indicators by country, a data
   quality summary, and the open query register -- so the figures can be
   shared with partners as a document, not just a link to the dashboard.
2. One Markdown report per country, reading like a data-quality reviewer's
   own notes: what changed since the last period, whether the country's own
   self-reported completeness/timeliness agrees with what this pipeline
   computed, whether its reconciliation self-attestation raised anything,
   what is still open in the query register, and a plain recommendation --
   contact the country, or no action needed. This is what orients the focal
   point's decision to follow up, not the raw database.

Nothing here recomputes an indicator: every figure comes from gold_indicator,
fact_quality or query_register exactly as transform.py and validate.py left
them (CLAUDE.md rule 1). Run after `run.py --transform --export`, against
the same store.

    python3 consolidate.py --workbook ../../reports/partner_workbook.xlsx
    python3 consolidate.py --reports-dir ../../reports/country
"""
from __future__ import annotations

import argparse
import os

from load import DB_DEFAULT, connect

HERE = os.path.dirname(os.path.abspath(__file__))

CONF_LABEL = {"high": "High", "medium": "Medium", "low": "Low", None: "Not reported"}
RECON_LABEL = {"Yes": "Reconciles", "No": "DOES NOT RECONCILE", None: "Not reported"}


# ------------------------------------------------------------- shared reads
def _latest_returns(con):
    """One row per country: its most recent, non-superseded return."""
    return con.execute(
        "SELECT r.*, q.facilities_expected, q.returns_complete, q.completeness,"
        " q.reported_completeness_pct, q.reported_timeliness_pct,"
        " q.conf_facilities, q.conf_patients, q.conf_workforce, q.conf_quality,"
        " q.conf_governance, q.recon_annex_a_vs_2_3, q.recon_patients_vs_2_5_2_6,"
        " q.recon_mentorship_vs_3_4, q.recon_definition_changed, q.recon_figure_corrected"
        " FROM fact_return r LEFT JOIN fact_quality q USING(return_id)"
        " WHERE r.superseded=0 AND r.period_id = ("
        "   SELECT MAX(r2.period_id) FROM fact_return r2"
        "   WHERE r2.iso3=r.iso3 AND r2.superseded=0)"
        " ORDER BY r.iso3").fetchall()


def _previous_return(con, iso3, period_id):
    return con.execute(
        "SELECT return_id, period_id FROM fact_return"
        " WHERE iso3=? AND superseded=0 AND verdict!='hold' AND period_id<?"
        " ORDER BY period_id DESC LIMIT 1", (iso3, period_id)).fetchone()


def _open_queries(con, return_id):
    return con.execute(
        "SELECT severity, section, field, observed, expected, question"
        " FROM query_register WHERE return_id=? AND status='open'"
        " ORDER BY CASE severity WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END",
        (return_id,)).fetchall()


def _latest_gold(con, iso3):
    return con.execute(
        "SELECT indicator_code, numerator, denominator, value, unit, suppressed"
        " FROM gold_indicator WHERE iso3=? AND disagg_key='all' AND period_id = ("
        "   SELECT MAX(period_id) FROM gold_indicator g2"
        "   WHERE g2.iso3=gold_indicator.iso3 AND g2.indicator_code=gold_indicator.indicator_code)",
        (iso3,)).fetchall()


def _patient_stock_delta(con, iso3, return_id, prev_return_id):
    """Ever-enrolled and active-in-care per condition, this period vs. last."""
    cur = {r["condition"]: r for r in con.execute(
        "SELECT condition, ever_enrolled, active_end FROM fact_patient_stock"
        " WHERE return_id=?", (return_id,))}
    prev = {r["condition"]: r for r in con.execute(
        "SELECT condition, ever_enrolled, active_end FROM fact_patient_stock"
        " WHERE return_id=?", (prev_return_id,))} if prev_return_id else {}
    out = []
    for cond, row in cur.items():
        if cond == "total":
            continue
        p = prev.get(cond)
        out.append({
            "condition": cond,
            "ever_enrolled": row["ever_enrolled"], "prev_ever_enrolled": p["ever_enrolled"] if p else None,
            "active_end": row["active_end"], "prev_active_end": p["active_end"] if p else None,
        })
    return out


# --------------------------------------------------------------- the report
def country_report(con, iso3: str) -> str:
    """A Markdown data-quality report for one country's latest return."""
    ret = con.execute(
        "SELECT r.*, c.name, q.facilities_expected, q.returns_complete, q.completeness,"
        " q.reported_completeness_pct, q.reported_timeliness_pct,"
        " q.recon_annex_a_vs_2_3, q.recon_patients_vs_2_5_2_6, q.recon_mentorship_vs_3_4,"
        " q.recon_definition_changed, q.recon_figure_corrected"
        " FROM fact_return r JOIN dim_country c USING(iso3)"
        " LEFT JOIN fact_quality q USING(return_id)"
        " WHERE r.iso3=? AND r.superseded=0"
        " ORDER BY r.period_id DESC LIMIT 1", (iso3,)).fetchone()
    if not ret:
        return f"# {iso3}\n\nNo return on file for this country.\n"

    lines = [f"# Data quality report: {ret['name']} ({iso3})",
             f"Period: **{ret['period_id']}**  ·  Source: {ret['source_kind']}"
             f"  ·  Verdict: **{ret['verdict']}**", ""]

    # ---- self-reported vs computed completeness/timeliness
    lines.append("## Reporting completeness and timeliness")
    if ret["completeness"] is not None:
        computed_pct = round(ret["completeness"] * 100)
        lines.append(f"- Computed from facility-return counts: **{computed_pct}%** "
                      f"({ret['returns_complete']} of {ret['facilities_expected']} facilities)")
    else:
        lines.append("- Computed completeness: not available (facility-return counts not reported)")
    if ret["reported_completeness_pct"] is not None:
        lines.append(f"- Self-reported by the country (indicator 5.1): "
                      f"**{ret['reported_completeness_pct']}%**")
        if ret["completeness"] is not None:
            gap = abs(round(ret["completeness"] * 100) - ret["reported_completeness_pct"])
            if gap > 10:
                lines.append(f"  - ⚠ **{gap} percentage points apart from the computed figure** "
                              "-- worth asking the country to explain before publishing either.")
    if ret["reported_timeliness_pct"] is not None:
        lines.append(f"- Self-reported timeliness: **{ret['reported_timeliness_pct']}%**")
    lines.append("")

    # ---- reconciliation self-attestation
    recon_items = [
        ("Facility counts in Annex A reconcile with indicator 2.3", ret["recon_annex_a_vs_2_3"]),
        ("Patient totals reconcile with indicators 2.5 and 2.6", ret["recon_patients_vs_2_5_2_6"]),
        ("Mentorship totals reconcile with indicator 3.4", ret["recon_mentorship_vs_3_4"]),
    ]
    if any(v is not None for _, v in recon_items):
        lines.append("## The country's own reconciliation check")
        for label, value in recon_items:
            lines.append(f"- {label}: **{RECON_LABEL.get(value, value or 'Not reported')}**")
        if ret["recon_definition_changed"] == "Yes":
            lines.append("- ⚠ The country reports a change in definitions, source systems, "
                          "or deduplication method since the last return.")
        if ret["recon_figure_corrected"] == "Yes":
            lines.append("- ℹ The country reports a correction to a previously reported figure.")
        lines.append("")

    # ---- period-over-period comparison
    prev = _previous_return(con, iso3, ret["period_id"])
    lines.append(f"## Compared to {prev['period_id'] if prev else 'the previous period'}")
    if not prev:
        lines.append("- No prior accepted return to compare against (first return, or every "
                      "earlier one was held).")
    else:
        deltas = _patient_stock_delta(con, iso3, ret["return_id"], prev["return_id"])
        any_row = False
        for d in deltas:
            if d["ever_enrolled"] is None or d["prev_ever_enrolled"] is None:
                continue
            any_row = True
            change = d["ever_enrolled"] - d["prev_ever_enrolled"]
            flag = ""
            if d["prev_ever_enrolled"] > 0 and d["ever_enrolled"] > d["prev_ever_enrolled"] * 2:
                flag = "  ⚠ more than doubled"
            elif change < 0:
                flag = "  ⚠ decreased (ever-enrolled is cumulative and should not fall)"
            lines.append(f"- **{d['condition']}** ever enrolled: {d['prev_ever_enrolled']} "
                         f"→ {d['ever_enrolled']} ({'+' if change >= 0 else ''}{change}){flag}")
        if not any_row:
            lines.append("- No comparable per-condition figures in both periods.")
    lines.append("")

    # ---- open queries
    queries = _open_queries(con, ret["return_id"])
    lines.append(f"## Open queries ({len(queries)})")
    if not queries:
        lines.append("- None.")
    else:
        for q in queries:
            lines.append(f"- **{q['severity']}** ({q['section']}, {q['field']}): {q['question']}")
    lines.append("")

    # ---- recommendation
    high = [q for q in queries if q["severity"] == "High"]
    medium = [q for q in queries if q["severity"] == "Medium"]
    recon_no = any(v == "No" for _, v in recon_items)
    lines.append("## Recommended action")
    if ret["verdict"] == "hold" or high:
        lines.append("**Contact the country.** This return is on hold or has a High-severity "
                      "open query: the figures should not be treated as final until resolved.")
    elif recon_no or medium:
        lines.append("**Follow up with the country.** Nothing blocks publication, but the "
                      "reconciliation self-attestation or a Medium-severity query raises "
                      "something worth a clarifying question.")
    else:
        lines.append("**No action needed.** No open High or Medium query, and the country's own "
                      "reconciliation check raised nothing.")
    lines.append("")
    return "\n".join(lines)


def all_country_reports(con, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for row in con.execute("SELECT DISTINCT iso3 FROM fact_return WHERE superseded=0 ORDER BY iso3"):
        iso3 = row["iso3"]
        path = os.path.join(out_dir, f"{iso3}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(country_report(con, iso3))
        written.append(path)
    return written


# -------------------------------------------------------------- the workbook
def build_workbook(con, out_path: str) -> None:
    """A partner-facing .xlsx: indicators by country, a data-quality summary,
    and the full open query register. Three sheets, nothing pivoted or
    styled beyond a bold header row -- this is a shareable snapshot, not a
    second front end."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    bold = Font(bold=True)

    latest = _latest_returns(con)
    countries = {r["iso3"]: r for r in latest}
    codes = [r["indicator_code"] for r in con.execute(
        "SELECT indicator_code FROM dim_indicator ORDER BY indicator_code")]

    ws = wb.active
    ws.title = "Indicators by country"
    ws.append(["Country", "Period", *codes])
    for cell in ws[1]:
        cell.font = bold
    for iso3 in sorted(countries):
        gold = {g["indicator_code"]: g for g in _latest_gold(con, iso3)}
        row = [iso3, countries[iso3]["period_id"]]
        for code in codes:
            g = gold.get(code)
            row.append(None if not g or g["suppressed"] else g["value"])
        ws.append(row)

    ws2 = wb.create_sheet("Data quality")
    ws2.append(["Country", "Period", "Source", "Verdict", "Completeness %",
                "Self-reported completeness %", "Self-reported timeliness %",
                "Annex A vs 2.3", "Patients vs 2.5/2.6", "Mentorship vs 3.4"])
    for cell in ws2[1]:
        cell.font = bold
    for iso3 in sorted(countries):
        r = countries[iso3]
        ws2.append([
            iso3, r["period_id"], r["source_kind"], r["verdict"],
            round(r["completeness"] * 100) if r["completeness"] is not None else None,
            r["reported_completeness_pct"], r["reported_timeliness_pct"],
            r["recon_annex_a_vs_2_3"], r["recon_patients_vs_2_5_2_6"], r["recon_mentorship_vs_3_4"],
        ])

    ws3 = wb.create_sheet("Open queries")
    ws3.append(["Country", "Period", "Severity", "Section", "Field", "Observed", "Expected", "Question"])
    for cell in ws3[1]:
        cell.font = bold
    for row in con.execute(
            "SELECT r.iso3, r.period_id, qr.severity, qr.section, qr.field, qr.observed,"
            " qr.expected, qr.question FROM query_register qr JOIN fact_return r USING(return_id)"
            " WHERE r.superseded=0 AND qr.status='open'"
            " ORDER BY r.iso3, CASE qr.severity WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END"):
        ws3.append(list(row))

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    wb.save(out_path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--workbook", help="Write the consolidated partner workbook to this path")
    ap.add_argument("--reports-dir", help="Write one per-country Markdown report into this directory")
    a = ap.parse_args()
    con = connect(a.db)

    if not a.workbook and not a.reports_dir:
        ap.error("pass --workbook, --reports-dir, or both")

    if a.workbook:
        build_workbook(con, a.workbook)
        print(f"partner workbook written to {a.workbook}")
    if a.reports_dir:
        written = all_country_reports(con, a.reports_dir)
        print(f"{len(written)} country reports written to {a.reports_dir}")


if __name__ == "__main__":
    main()
