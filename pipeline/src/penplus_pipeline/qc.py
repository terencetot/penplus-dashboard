#!/usr/bin/env python3
"""
penplus_qc.py - Quality control on returned PEN-Plus monthly reporting forms.

Reads one or more completed .docx forms, applies a rule set, and writes an Excel
query register plus a ready-to-send query note per country.

    python3 penplus_qc.py returns/*.docx --history history.json --out queries.xlsx

Every rule produces a row with: what was observed, what was expected, and the
question to put to the country. Nothing is silently corrected.
"""

import argparse
import glob
import json
import os
import re
import statistics
import sys
from collections import OrderedDict

from docx import Document
from docx.oxml.ns import qn

W_T = qn("w:t")

# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

BLANKS = {"", "-", "n/a", "na", "choose", "select", "none"}
NOT_REPORTED = {"not reported", "nr", "not available", "unknown"}


def _text(el):
    """All text under an element, including drop-down content controls."""
    return "".join(t.text or "" for t in el.iter(W_T))


def cell_text(cell):
    return re.sub(r"\s+", " ", _text(cell._tc)).strip()


def iter_body(doc):
    """Yield ('p', text) and ('tbl', Table) in document order."""
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    body = doc.element.body
    tables = iter(doc.tables)
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield "p", re.sub(r"\s+", " ", _text(child)).strip()
        elif child.tag == qn("w:tbl"):
            yield "tbl", next(tables)


SECTION_RE = re.compile(r"^(\d+(?:\.\d+)?)[.\s]")


def parse_form(path):
    """Return {'_file':..., 'id':{}, '2.1':[rows], ...} where rows are lists of cell strings."""
    doc = Document(path)
    out = {"_file": os.path.basename(path)}
    current = None
    for kind, item in iter_body(doc):
        if kind == "p":
            m = SECTION_RE.match(item)
            if m and len(item) < 90:
                current = m.group(1)
        else:
            rows = [[cell_text(c) for c in r.cells] for r in item.rows]
            if current is None:
                continue
            key = current
            if key in out:              # a second table under the same heading
                out.setdefault(key + "_extra", []).extend(rows)
                continue
            out[key] = rows
    return out


def num(v):
    """Parse a reported value into a float, or None if it is not a number."""
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in BLANKS or s in NOT_REPORTED:
        return None
    s = s.replace(",", "").replace(" ", "").replace("%", "")
    s = re.sub(r"(usd|\$|over|>|<|~|approx\.?|about)", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def is_blank(v):
    return str(v).strip().lower() in BLANKS


APPROX = re.compile(r"(over|about|approx|~|>|<|\+)", re.I)


def is_approx(v):
    """A value that parses as a number but was written with a qualifier."""
    return (not is_blank(v)) and num(v) is not None and bool(APPROX.search(str(v)))


def raw_is_text(v):
    """True when a value was supplied but is not parseable as a number."""
    return (not is_blank(v)) and str(v).strip().lower() not in NOT_REPORTED and num(v) is None


# --------------------------------------------------------------------------
# query register
# --------------------------------------------------------------------------

class Register:
    def __init__(self, country, period, filename):
        self.country, self.period, self.file = country, period, filename
        self.rows = []

    def add(self, severity, section, field, observed, expected, question):
        self.rows.append(OrderedDict(
            country=self.country, period=self.period, file=self.file,
            severity=severity, section=section, field=field,
            observed=observed, expected=expected, question=question))

    # convenience
    def high(self, *a): self.add("High", *a)
    def med(self, *a): self.add("Medium", *a)
    def low(self, *a): self.add("Low", *a)


# --------------------------------------------------------------------------
# rules
# --------------------------------------------------------------------------

def _table(form, key, min_cols=2):
    t = form.get(key)
    if not t or len(t) < 2:
        return []
    return [r for r in t[1:] if len(r) >= min_cols]


def rule_identification(form, reg):
    rows = form.get("1", [])
    got = {r[0].lower(): r[1] for r in rows if len(r) >= 2}
    for label in ["country", "reporting month", "reporting year",
                  "npo name, who country office", "npo email",
                  "national programme focal point", "date the form was completed"]:
        v = next((v for k, v in got.items() if k.startswith(label[:18])), "")
        if is_blank(v):
            reg.high("1", label.title(), "empty", "a value",
                     f"The field '{label}' was left empty. Please complete it so the return can be filed.")
    email = next((v for k, v in got.items() if "email" in k), "")
    if not is_blank(email) and "@" not in email:
        reg.med("1", "NPO email", email, "an email address",
                "The NPO email does not look like an address. Please confirm the contact.")


def rule_standing(form, reg):
    for r in _table(form, "2.1", 4):
        item, on_record, change, date = r[0], r[1], r[2], r[3]
        if not item:
            continue
        if is_blank(on_record) and is_blank(change):
            reg.med("2.1", item, "no status", "a status on record or a change",
                    f"No status is recorded for '{item}'. Please select one from the drop-down list.")
        changed = (not is_blank(change)) and change.lower() != "no change"
        if changed and is_blank(date):
            reg.high("2.1", item, f"change '{change}' with no date", "a month and year",
                     f"'{item}' is reported as changed ({change}) but no date is given. "
                     "Please state the month and year of the change and the supporting document.")
        if on_record.lower() == "yes" and change.lower() == "now no":
            reg.high("2.1", item, "Yes reverted to No", "an explanation",
                     f"'{item}' was previously reported as achieved and is now reported as No. "
                     "Please confirm and explain what was withdrawn or superseded.")


def rule_sites_and_coverage(form, reg, parsed):
    site_rows = [r for r in _table(form, "2.2", 5) if any(not is_blank(c) for c in r[:4])]
    parsed["site_rows"] = len(site_rows)
    for r in site_rows:
        name, district, conds, partner, status = (r + [""] * 5)[:5]
        if is_blank(district):
            reg.med("2.2", f"Site {name}", "no district", "a district",
                    f"The site '{name}' has no district. Please complete it so the site can be mapped.")
        if is_blank(conds):
            reg.med("2.2", f"Site {name}", "no conditions", "the conditions managed",
                    f"The site '{name}' does not state which conditions it manages.")
        if is_blank(status):
            reg.low("2.2", f"Site {name}", "no status", "a status",
                    f"Please select a status for the site '{name}'.")

    cov = {r[0].lower(): r[1] for r in _table(form, "2.3", 2)}

    def cv(frag):
        return next((v for k, v in cov.items() if frag in k), "")

    total_sites = num(cv("total number of pen-plus sites"))
    districts = num(cv("health districts implementing"))
    all_districts = num(cv("total number of health districts"))
    parsed.update(total_sites=total_sites, districts=districts)

    if total_sites is None:
        reg.high("2.3", "Total sites", "empty", "a number",
                 "The total number of PEN-Plus sites is missing.")
    elif len(site_rows) and abs(total_sites - len(site_rows)) > 0.5:
        reg.high("2.3", "Total sites", f"{total_sites:g} stated, {len(site_rows)} listed",
                 "the two to agree",
                 f"The form lists {len(site_rows)} sites but states a total of {total_sites:g}. "
                 "Please confirm which is correct and list any missing site.")
    if districts is not None and all_districts is not None and districts > all_districts:
        reg.high("2.3", "Districts", f"{districts:g} of {all_districts:g}",
                 "implementing districts to be no more than the national total",
                 "More districts are reported as implementing PEN-Plus than exist in the country. "
                 "Please check both figures.")
    if districts is not None and total_sites is not None and districts > total_sites:
        reg.med("2.3", "Districts vs sites", f"{districts:g} districts, {total_sites:g} sites",
                "districts covered to be supported by at least as many sites",
                "More districts are reported than there are PEN-Plus sites. Please confirm whether "
                "some districts are served by a site located in another district.")


CONDITIONS = ["sickle cell disease", "type 1 diabetes", "type 2 diabetes",
              "rheumatic heart disease", "congenital heart disease", "cardiomyopathy",
              "severe hypertension", "asthma or copd", "other"]


def rule_patients(form, reg, parsed):
    rows = _table(form, "3.1", 7)
    body = [r for r in rows if r[0].strip().lower() in CONDITIONS]
    total = next((r for r in rows if r[0].strip().lower() == "total"), None)
    cols = ["Newly enrolled this month", "Enrolled to date", "Active in care at end of month",
            "Transferred out", "Lost to follow-up", "Died"]

    for r in body:
        cond = r[0]
        for j, cname in enumerate(cols, start=1):
            v = r[j]
            if is_blank(v):
                reg.med("3.1", f"{cond} / {cname}", "empty", "a number, 0, or Not reported",
                        f"'{cname}' is empty for {cond}. Please enter a figure, or 0, or "
                        "\"Not reported\" so that an empty cell is not read as zero.")
            elif raw_is_text(v):
                reg.med("3.1", f"{cond} / {cname}", v, "a number",
                        f"'{v}' was entered for {cond} under '{cname}'. Please give a plain figure.")
            elif is_approx(v):
                reg.med("3.1", f"{cond} / {cname}", v, "an exact count",
                        f"'{v}' is an approximation. The regional dataset needs an exact count, "
                        "or \"Not reported\" if the register cannot give one.")
        new, ever, active, tout, ltfu, died = [num(r[j]) for j in range(1, 7)]
        if ever is not None and active is not None and active > ever:
            reg.high("3.1", f"{cond} / active vs cumulative", f"{active:g} active, {ever:g} ever enrolled",
                     "active to be no greater than cumulative",
                     f"For {cond}, more patients are active than have ever been enrolled. Please check.")
        if new is not None and ever is not None and new > ever:
            reg.high("3.1", f"{cond} / new vs cumulative", f"{new:g} new, {ever:g} ever enrolled",
                     "new to be part of cumulative",
                     f"For {cond}, this month's new enrolments exceed the cumulative total.")
        if active and died is not None and died > active:
            reg.med("3.1", f"{cond} / deaths", f"{died:g} deaths, {active:g} active",
                    "deaths to be a small share of the cohort",
                    f"For {cond}, deaths this month exceed the number of active patients. Please confirm.")
        if active and ltfu is not None and active > 0 and ltfu > 0.5 * active:
            reg.med("3.1", f"{cond} / loss to follow-up", f"{ltfu:g} of {active:g} active",
                    "an unusual attrition level",
                    f"For {cond}, more than half the active cohort is reported lost to follow-up "
                    "this month. Please confirm and explain.")

    for j, cname in enumerate(cols, start=1):
        s = sum(v for v in (num(r[j]) for r in body) if v is not None)
        tv = num(total[j]) if total else None
        if tv is not None and abs(tv - s) > 0.5:
            reg.high("3.1", f"Total / {cname}", f"{tv:g} stated, {s:g} from the rows",
                     "the total to equal the sum of its cells",
                     f"The total for '{cname}' does not equal the sum of the conditions above it "
                     f"({tv:g} against {s:g}). Please tell us which figure is correct.")

    parsed["ever_by_condition"] = {r[0].strip().lower(): num(r[2]) for r in body}
    parsed["new_total"] = sum(v for v in (num(r[1]) for r in body) if v is not None)
    parsed["ever_total"] = sum(v for v in (num(r[2]) for r in body) if v is not None)
    parsed["active_total"] = sum(v for v in (num(r[3]) for r in body) if v is not None)
    parsed["out_total"] = sum(v for v in (num(r[j]) for r in body for j in (4, 5, 6)) if v is not None)

    non_std = [r[0] for r in body
               if r[0].strip().lower() in ("type 2 diabetes", "severe hypertension", "asthma or copd")
               and (num(r[3]) or 0) > 0]
    if non_std:
        reg.low("3.1", "Scope of the cohort", ", ".join(non_std),
                "a note on what is included",
                "Patients are reported under conditions that several countries do not include in "
                "PEN-Plus. This is not an error, but please confirm it so the regional total is "
                "built on a like-for-like basis.")


def rule_continuity(form, reg):
    for r in _table(form, "3.2", 4):
        label = r[0]
        if label.strip().lower() == "total" or not label:
            continue
        ret = num(r[3])
        if ret is not None and not (0 <= ret <= 100):
            reg.high("3.2", f"{label} / retention", r[3], "a percentage between 0 and 100",
                     f"The 12-month retention reported for {label} is outside the 0 to 100 range.")
        visits, intarget = num(r[1]), num(r[2])
        if visits is not None and intarget is not None and intarget > visits and visits > 0:
            reg.med("3.2", f"{label} / measurements", f"{intarget:g} in target, {visits:g} visits",
                    "measurements to come from visits",
                    f"For {label}, more patients are reported within target than there were "
                    "follow-up visits. Please confirm the basis of the measurement.")


def rule_staff(form, reg, parsed):
    rows = _table(form, "3.3", 4)
    cadres = [r for r in rows if not r[0].lower().startswith("total")
              and "primary health care" not in r[0].lower() and r[0]]
    total = next((r for r in rows if r[0].lower().startswith("total")), None)
    for j, cname in enumerate(["Trained this month", "Trained to date", "In post at a PEN-Plus site"], start=1):
        s = sum(v for v in (num(r[j]) for r in cadres) if v is not None)
        tv = num(total[j]) if total else None
        if tv is not None and abs(tv - s) > 0.5:
            reg.high("3.3", f"Total / {cname}", f"{tv:g} stated, {s:g} from the rows",
                     "the total to equal the sum of the cadres",
                     f"The staff total for '{cname}' does not match the sum of the cadres "
                     f"({tv:g} against {s:g}). Please confirm which is correct.")
    for r in cadres:
        todate, inpost = num(r[2]), num(r[3])
        if todate is not None and inpost is not None and inpost > todate:
            reg.high("3.3", f"{r[0]} / in post", f"{inpost:g} in post, {todate:g} trained",
                     "in post to be a subset of those trained",
                     f"More {r[0].lower()} are reported in post at PEN-Plus sites than have been trained.")
    if total:
        parsed["trained_to_date"] = num(total[2])


CASCADES = [
    (["newborns and children under five screened", "of whom screened positive", "of whom started on care"],
     "sickle cell screening"),
    (["blood glucose tests performed", "suspected type 1 diabetes cases identified",
      "of whom referred to a pen-plus site", "of whom confirmed and initiated on insulin"],
     "type 1 diabetes case finding"),
]


def rule_screening(form, reg):
    rows = _table(form, "3.5", 2)
    vals = OrderedDict((r[0].strip().lower(), r[1]) for r in rows if r[0])
    for steps, label in CASCADES:
        seq = []
        for frag in steps:
            key = next((k for k in vals if k.startswith(frag[:28])), None)
            seq.append((frag, num(vals.get(key)) if key else None))
        for (an, av), (bn, bv) in zip(seq, seq[1:]):
            if av is not None and bv is not None and bv > av:
                reg.high("3.5", f"{label}", f"{bn} = {bv:g} exceeds {an} = {av:g}",
                         "each step of the cascade to be no larger than the one before",
                         f"In the {label} cascade, '{bn}' is larger than '{an}'. "
                         "Please check the two figures.")
        present = [v for _, v in seq if v is not None]
        if len(present) >= 2 and present[0] and present[-1] / present[0] < 0.05:
            reg.med("3.5", label, f"{present[-1]:g} of {present[0]:g}",
                    "attrition worth explaining",
                    f"Fewer than 5% of those entering the {label} pathway reach the last step. "
                    "Please comment on where patients are lost.")


def rule_medicines(form, reg):
    for r in _table(form, "3.6", 3):
        product, avail, days = (r + [""] * 3)[:3]
        if not product:
            continue
        if is_blank(avail):
            reg.med("3.6", product, "no availability", "a value from the list",
                    f"Please select an availability for {product}.")
        d = num(days)
        if avail.lower().startswith("always") and d and d > 0:
            reg.high("3.6", product, f"always available, {d:g} days out of stock",
                     "the two answers to agree",
                     f"{product} is reported as always available yet {d:g} days out of stock. "
                     "Please reconcile.")
        if avail.lower().startswith("never") and d is not None and d == 0:
            reg.med("3.6", product, "never available, 0 days out of stock",
                    "the two answers to agree",
                    f"{product} is reported as never available but with no days out of stock.")
        if d is not None and d > 31:
            reg.med("3.6", product, f"{d:g} days", "at most 31 days in a month",
                    f"Days out of stock for {product} exceed the length of the month.")


def rule_partners(form, reg, parsed):
    rows = [r for r in _table(form, "3.7", 4) if any(not is_blank(c) for c in r)]
    s = sum(v for v in (num(r[3]) for r in rows) if v is not None)
    total_sites = parsed.get("total_sites")
    if total_sites and s > total_sites:
        reg.med("3.7", "Sites supported by partners", f"{s:g} against {total_sites:g} sites",
                "partner support not to be double counted",
                f"Partners together report supporting {s:g} sites while the country has "
                f"{total_sites:g}. Where two partners support the same site, please say so, "
                "so that the site is counted once.")
    for r in rows:
        if is_blank(r[2]):
            reg.low("3.7", f"Partner {r[0]}", "no role", "a role from the list",
                    f"Please select a role for {r[0]}.")


def rule_narrative(form, reg, parsed):
    notes = " ".join(" ".join(r) for r in form.get("4", []))
    notes = re.sub(r"Sources of the figures[^.]*month", "", notes, flags=re.I).strip()
    if len(notes) < 25:
        reg.med("4", "Sources and comments", "empty or very short", "a short note",
                "Section 4 is empty. Please state the source of the figures and the closing "
                "date of the period, so the return can be used without further exchange.")
    parsed["notes_len"] = len(notes)


# ---- longitudinal rules, against previous returns ------------------------

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


def period_key(form):
    rows = form.get("1", [])
    got = {r[0].lower(): r[1] for r in rows if len(r) >= 2}
    month = next((v for k, v in got.items() if k.startswith("reporting month")), "").strip()
    year = next((v for k, v in got.items() if k.startswith("reporting year")), "").strip()
    mi = MONTHS.index(month.lower()) + 1 if month.lower() in MONTHS else 0
    return f"{year}-{mi:02d}" if year else month


def country_of(form):
    rows = form.get("1", [])
    got = {r[0].lower(): r[1] for r in rows if len(r) >= 2}
    return next((v for k, v in got.items() if k.startswith("country")), "").strip() or "Unknown"


def rule_longitudinal(parsed, reg, history):
    key = parsed["country"]
    past = sorted([h for h in history.get(key, []) if h["period"] < parsed["period"]],
                  key=lambda h: h["period"])
    if not past:
        return
    prev = past[-1]

    for field, label in [("ever_total", "cumulative enrolment"),
                         ("trained_to_date", "health workers trained to date"),
                         ("total_sites", "number of sites")]:
        now, before = parsed.get(field), prev.get(field)
        if now is None or before is None:
            continue
        if now < before - 0.5:
            reg.high("longitudinal", label, f"{now:g} now, {before:g} in {prev['period']}",
                     "a cumulative figure never to fall",
                     f"The {label} is lower than last month ({now:g} against {before:g}). "
                     "A cumulative figure cannot decrease. Please confirm which month is wrong.")

    now, before = parsed.get("active_total"), prev.get("active_total")
    newp, outp = parsed.get("new_total"), parsed.get("out_total")
    if None not in (now, before, newp, outp):
        expected = before + newp - outp
        if abs(now - expected) > max(2, 0.05 * max(expected, 1)):
            reg.high("longitudinal", "cohort identity",
                     f"{now:g} active, {expected:g} expected",
                     "active = previous active + new - transfers - losses - deaths",
                     f"The active cohort does not reconcile with last month: "
                     f"{before:g} + {newp:g} new - {outp:g} exits gives {expected:g}, "
                     f"but {now:g} is reported. Please explain the difference.")

    now_c = parsed.get("ever_by_condition") or {}
    before_c = prev.get("ever_by_condition") or {}
    for cond, before_v in before_c.items():
        now_v = now_c.get(cond)
        if before_v is None or now_v is None:
            continue
        if now_v < before_v - 0.5:
            reg.high("longitudinal", f"cumulative enrolment, {cond}",
                     f"{now_v:g} now, {before_v:g} in {prev['period']}",
                     "a cumulative figure never to fall",
                     f"Cumulative enrolment for {cond} is lower than last month "
                     f"({now_v:g} against {before_v:g}). Please confirm which month is wrong.")

    series = [h.get("new_total") for h in past if h.get("new_total") is not None]
    if len(series) >= 3 and parsed.get("new_total") is not None:
        med = statistics.median(series)
        if med > 0 and parsed["new_total"] > 4 * med:
            reg.med("longitudinal", "new enrolments", f"{parsed['new_total']:g} against a median of {med:g}",
                    "a change in line with the trend",
                    "New enrolments are more than four times the country's usual monthly level. "
                    "Please confirm the figure and say what drove the increase.")
        if med > 0 and parsed["new_total"] < 0.2 * med:
            reg.med("longitudinal", "new enrolments", f"{parsed['new_total']:g} against a median of {med:g}",
                    "a change in line with the trend",
                    "New enrolments are well below the country's usual monthly level. "
                    "Please confirm whether this reflects a real fall or incomplete reporting.")


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def check_form(path, history):
    form = parse_form(path)
    country, period = country_of(form), period_key(form)
    reg = Register(country, period, form["_file"])
    parsed = {"country": country, "period": period}

    rule_identification(form, reg)
    rule_standing(form, reg)
    rule_sites_and_coverage(form, reg, parsed)
    rule_patients(form, reg, parsed)
    rule_continuity(form, reg)
    rule_staff(form, reg, parsed)
    rule_screening(form, reg)
    rule_medicines(form, reg)
    rule_partners(form, reg, parsed)
    rule_narrative(form, reg, parsed)
    rule_longitudinal(parsed, reg, history)
    return reg, parsed


def query_note(reg):
    if not reg.rows:
        return (f"Dear colleague,\n\nThank you for the {reg.period} PEN-Plus return for "
                f"{reg.country}. The form passed all consistency checks and no clarification "
                "is needed.\n\nKind regards,\nNCD and Mental Health team, WHO Regional Office for Africa\n")
    lines = [f"Dear colleague,", "",
             f"Thank you for the {reg.period} PEN-Plus return for {reg.country}. "
             "Before the figures are consolidated into the regional dataset, we would be grateful "
             "for clarification on the following points.", ""]
    n = 0
    for sev in ("High", "Medium", "Low"):
        block = [r for r in reg.rows if r["severity"] == sev]
        if not block:
            continue
        for r in block:
            n += 1
            lines.append(f"{n}. Section {r['section']}, {r['field']}. {r['question']}")
            lines.append(f"   Reported: {r['observed']}.")
            lines.append("")
    lines += ["A reply on the points above would allow us to close the return. "
              "Where a figure is confirmed as correct, a short note is sufficient.", "",
              "Kind regards,", "NCD and Mental Health team, WHO Regional Office for Africa", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("forms", nargs="+", help="completed .docx forms (globs allowed)")
    ap.add_argument("--history", default=None, help="JSON file of previously parsed returns")
    ap.add_argument("--out", default="penplus_queries.xlsx")
    ap.add_argument("--notes-dir", default=None, help="write one query note per country here")
    args = ap.parse_args()

    paths = []
    for f in args.forms:
        paths.extend(sorted(glob.glob(f)) or [f])

    history = {}
    if args.history and os.path.exists(args.history):
        history = json.load(open(args.history))

    all_rows, summary, notes = [], [], {}
    for path in paths:
        try:
            reg, parsed = check_form(path, history)
        except Exception as exc:                      # a form that cannot be read is itself a finding
            all_rows.append(OrderedDict(
                country="Unknown", period="", file=os.path.basename(path), severity="High",
                section="file", field="structure", observed=str(exc)[:160],
                expected="the standard form, unmodified",
                question="The file could not be read against the standard template. Please resend "
                         "the return on the official form without altering the tables."))
            continue
        all_rows.extend(reg.rows)
        notes[f"{reg.country}_{reg.period}"] = query_note(reg)
        counts = {s: sum(1 for r in reg.rows if r["severity"] == s) for s in ("High", "Medium", "Low")}
        summary.append(OrderedDict(country=reg.country, period=reg.period, file=reg.file,
                                   high=counts["High"], medium=counts["Medium"], low=counts["Low"],
                                   status="Hold" if counts["High"] else
                                          ("Query" if counts["Medium"] else "Accept"),
                                   **{k: v for k, v in parsed.items() if k not in ("country", "period")}))
        history.setdefault(parsed["country"], [])
        history[parsed["country"]] = [h for h in history[parsed["country"]]
                                      if h["period"] != parsed["period"]] + [parsed]

    try:
        import pandas as pd
        with pd.ExcelWriter(args.out, engine="openpyxl") as xl:
            pd.DataFrame(summary).to_excel(xl, sheet_name="Summary", index=False)
            pd.DataFrame(all_rows).to_excel(xl, sheet_name="Queries", index=False)
        print(f"wrote {args.out}: {len(all_rows)} queries over {len(summary)} returns")
    except ImportError:
        print(json.dumps(all_rows, indent=2))

    if args.history:
        json.dump(history, open(args.history, "w"), indent=1)
    if args.notes_dir:
        os.makedirs(args.notes_dir, exist_ok=True)
        for name, body in notes.items():
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
            open(os.path.join(args.notes_dir, f"query_{safe}.txt"), "w").write(body)
        print(f"wrote {len(notes)} query notes to {args.notes_dir}")

    return 1 if any(r["severity"] == "High" for r in all_rows) else 0


if __name__ == "__main__":
    sys.exit(main())
