#!/usr/bin/env python3
"""
export.py - write the static JSON bundle the dashboard reads.

One file per screen, plus a manifest. The bundle is the API: the site makes no
network call beyond loading these files, and performs no calculation on them.
"""
from __future__ import annotations

import json
import os

from load import DB_DEFAULT, connect

HERE = os.path.dirname(os.path.abspath(__file__))
# HERE = <repo>/pipeline/src/penplus_pipeline -> <repo>/site/public/data
# The bundle lives under site/public so Vite serves and copies it verbatim;
# the built site still exposes it at /data, matching the specification.
OUT_DEFAULT = os.path.join(HERE, "..", "..", "..", "site", "public", "data")


def _d(rows):
    return [dict(r) for r in rows]


def _redact_facility(f: dict) -> dict:
    """Facility identity is not for public consumption (CLAUDE.md, "internal
    view only"). Everything else about the facility stays -- status, scores,
    counts -- only what could identify it is withheld."""
    f = dict(f)
    f["name"] = None
    f["district"] = None
    f["region"] = None
    return f


def _redact_suppressed_gold(g: dict) -> dict:
    """A flag alone is not suppression: CLAUDE.md rule 7 is to withhold a
    numerator under five, not just mark it while still publishing it. The
    internal (non-public) export keeps the real number for programme staff;
    the public export -- the only one ever committed to this repository,
    since GitHub Pages has no non-public audience -- blanks it."""
    if not g["suppressed"]:
        return g
    g = dict(g)
    g["numerator"] = None
    g["denominator"] = None
    g["value"] = None
    return g


def export(db_path: str = DB_DEFAULT, out_dir: str = OUT_DEFAULT, public: bool = False):
    con = connect(db_path)
    out = os.path.abspath(out_dir)
    os.makedirs(os.path.join(out, "countries"), exist_ok=True)

    man = dict(con.execute("SELECT * FROM build_manifest").fetchone())
    man["suppress_below"] = 5
    man["public"] = public
    man["note"] = ("Values are pre-computed. null means not reported and is never zero. "
                   "basis='historical' marks a return rebuilt from pre-Phase Two evidence."
                   + (" This is the public export: facility identity is withheld and cells"
                      " under 5 are suppressed, not merely flagged." if public else ""))

    countries = _d(con.execute(
        "SELECT c.iso3, c.name, c.cohort,"
        " (SELECT COUNT(*) FROM fact_return r WHERE r.iso3=c.iso3 AND r.superseded=0) returns,"
        " (SELECT MAX(period_id) FROM fact_return r WHERE r.iso3=c.iso3 AND r.superseded=0) last_period"
        " FROM dim_country c ORDER BY c.name"))
    indicators = _d(con.execute("SELECT * FROM dim_indicator ORDER BY indicator_code"))
    gold = _d(con.execute("SELECT * FROM gold_indicator"))

    latest = {}
    for g in gold:
        if g["disagg_key"] != "all":
            continue
        k = (g["iso3"], g["indicator_code"])
        if k not in latest or g["period_id"] > latest[k]["period_id"]:
            latest[k] = g

    def headline(code):
        vals = [v["numerator"] for (i, c), v in latest.items()
                if c == code and v["numerator"] is not None]
        return {"total": sum(vals) if vals else None,
                "countries_reporting": len(vals),
                "countries_total": len(countries)}

    def regional_value(code, unit):
        """The one regional aggregate for `code`: sum of numerators for a
        count, or sum(numerator)/sum(denominator) for a rate. This is the
        only place that turns per-country gold rows into a regional figure
        for display -- the front end reads the result, it never sums a
        series itself (CLAUDE.md, "No arithmetic in the front end")."""
        rows = [v for (i, c), v in latest.items() if c == code]
        as_of = max((v["as_of"] for v in rows if v["as_of"]), default=None)
        if unit == "rate":
            nums = [v["numerator"] for v in rows if v["numerator"] is not None]
            dens = [v["denominator"] for v in rows if v["denominator"] is not None]
            value = (sum(nums) / sum(dens)) if (nums and dens and sum(dens) > 0) else None
        else:
            nums = [v["numerator"] for v in rows if v["numerator"] is not None]
            value = sum(nums) if nums else None
        return value, as_of, len(rows)

    # Every indicator carries its regional value and, once the Regional Office
    # publishes a target, its gap to milestone. dim_indicator.milestone is
    # None until then (see docs/architecture.md, "Milestones") -- the bundle
    # must say so rather than a screen fabricating a target.
    for dim in indicators:
        value, as_of, reporting = regional_value(dim["indicator_code"], dim["unit"])
        dim["regional_value"] = value
        dim["regional_as_of"] = as_of
        dim["countries_reporting"] = reporting
        dim["gap"] = (dim["milestone"] - value) if (dim["milestone"] is not None and value is not None) else None

    # The five headline indicators for the screen 1 milestone strip: the four
    # that feed the hero figures, plus facility quality as the capacity signal
    # the programme is held to alongside volume.
    HEADLINE_INDICATORS = ["2.3", "2.5", "2.6", "3.3", "2.4"]
    ind_by_code = {i["indicator_code"]: i for i in indicators}
    milestone_strip = [{
        "indicator_code": code,
        "label_en": ind_by_code[code]["label_en"],
        "unit": ind_by_code[code]["unit"],
        "value": ind_by_code[code]["regional_value"],
        "as_of": ind_by_code[code]["regional_as_of"],
        "milestone": ind_by_code[code]["milestone"],
        "gap": ind_by_code[code]["gap"],
        "countries_reporting": ind_by_code[code]["countries_reporting"],
        "countries_total": len(countries),
    } for code in HEADLINE_INDICATORS if code in ind_by_code]

    write = lambda name, obj: json.dump(
        obj, open(os.path.join(out, name), "w", encoding="utf-8"),
        ensure_ascii=False, indent=1)

    # Aggregation (headline, regional_value, milestone_strip, above) always
    # runs on the real per-country numbers, suppressed or not -- a withheld
    # country still counts toward the regional total. Redaction happens only
    # here, on the rows actually written out, and only for the public export.
    gold_out = [_redact_suppressed_gold(g) for g in gold] if public else gold
    latest_out = [_redact_suppressed_gold(v) for v in latest.values()] if public \
        else list(latest.values())

    write("manifest.json", man)
    write("overview.json", {
        "manifest": man,
        "headline": {"facilities": headline("2.3"), "ever_enrolled": headline("2.5"),
                     "active": headline("2.6"), "trained": headline("3.3")},
        "milestone_strip": milestone_strip,
        "countries": countries,
        "latest": latest_out,
    })
    write("indicators.json", {"manifest": man, "dim": indicators, "values": gold_out})
    open_queries = _d(con.execute(
        "SELECT r.iso3, r.period_id, qr.query_id, qr.severity, qr.section, qr.field,"
        " qr.observed, qr.expected, qr.question, qr.status, qr.raised_at"
        " FROM query_register qr JOIN fact_return r USING(return_id)"
        " WHERE r.superseded=0 AND qr.status='open'"
        " ORDER BY r.iso3, r.period_id, qr.severity"))

    quality_rows = _d(con.execute(
        "SELECT r.iso3, r.period_id, r.source_kind, r.verdict, r.ltfu_compliant,"
        " r.dedup_basis, r.patient_source, q.facilities_expected, q.returns_complete,"
        " q.completeness, q.conf_facilities, q.conf_patients, q.conf_workforce,"
        " q.conf_quality, q.conf_governance, q.returns_on_time,"
        " (SELECT COUNT(*) FROM query_register qr WHERE qr.return_id=r.return_id"
        "  AND qr.status='open') open_queries"
        " FROM fact_return r LEFT JOIN fact_quality q USING(return_id)"
        " WHERE r.superseded=0 ORDER BY r.iso3, r.period_id"))

    # The screen's headline figure is an average over each country's most
    # recent period, not every historical row -- computed here, once, so the
    # site never runs its own reduce() over the bundle (CLAUDE.md rule 1).
    latest_quality_by_country = {}
    for row in quality_rows:
        prev = latest_quality_by_country.get(row["iso3"])
        if not prev or row["period_id"] > prev["period_id"]:
            latest_quality_by_country[row["iso3"]] = row
    known_completeness = [r["completeness"] for r in latest_quality_by_country.values()
                          if r["completeness"] is not None]
    avg_completeness = (sum(known_completeness) / len(known_completeness)) if known_completeness else None
    below_threshold = sum(1 for r in latest_quality_by_country.values()
                          if r["completeness"] is not None and r["completeness"] < 0.8)

    write("quality.json", {
        "manifest": man,
        "avg_completeness": avg_completeness,
        "countries_below_threshold": below_threshold,
        "rows": quality_rows,
        "open_queries": open_queries})
    facility_rows = _d(con.execute(
        "SELECT f.*, fp.period_id_last, fp.active_end, fp.quality_score, fp.readiness_class"
        " FROM dim_facility f LEFT JOIN ("
        "   SELECT fp.facility_id, r.period_id period_id_last, fp.active_end,"
        "          fp.quality_score, fp.readiness_class"
        "   FROM fact_facility_period fp JOIN fact_return r USING(return_id)"
        "   WHERE r.superseded=0"
        "   GROUP BY fp.facility_id HAVING MAX(r.period_id)"
        " ) fp USING(facility_id) ORDER BY f.iso3, f.name"))
    scored = [f["quality_score"] for f in facility_rows if f["quality_score"] is not None]
    avg_quality_score = round(sum(scored) / len(scored)) if scored else None
    if public:
        facility_rows = [_redact_facility(f) for f in facility_rows]
    write("facilities.json", {
        "manifest": man,
        "avg_quality_score": avg_quality_score,
        "rows": facility_rows})

    for c in countries:
        iso3 = c["iso3"]
        country_gold = [g for g in gold if g["iso3"] == iso3]
        country_facilities = _d(con.execute(
            "SELECT * FROM dim_facility WHERE iso3=? ORDER BY name", (iso3,)))
        if public:
            country_gold = [_redact_suppressed_gold(g) for g in country_gold]
            country_facilities = [_redact_facility(f) for f in country_facilities]
        write(f"countries/{iso3}.json", {
            "manifest": man, "country": c,
            "values": country_gold,
            "facilities": country_facilities,
            # One row per milestone_code: the most recent period that reported
            # it, not every historical period stacked -- a milestone's status
            # is a current state, not a series to list in full (contrast
            # gold_indicator, which does publish every period for a trend).
            "governance": _d(con.execute(
                "SELECT g.*, r.period_id FROM fact_governance g JOIN fact_return r USING(return_id)"
                " WHERE r.iso3=? AND r.superseded=0"
                " AND r.period_id = ("
                "   SELECT MAX(r2.period_id) FROM fact_governance g2"
                "   JOIN fact_return r2 USING(return_id)"
                "   WHERE r2.iso3=r.iso3 AND r2.superseded=0 AND g2.milestone_code=g.milestone_code"
                " )"
                " ORDER BY g.milestone_code", (iso3,))),
            "open_queries": [q for q in open_queries if q["iso3"] == iso3],
        })

    total = sum(os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(out) for f in fs)
    print(f"bundle written to {out}: {total/1024:.0f} KB")


if __name__ == "__main__":
    export()
