#!/usr/bin/env python3
"""
geocode_facilities.py - coordinates for the facility register, by the rules of
docs/refinement/02_data/GEOCODING_PROTOCOL.md. Found and checked, never guessed.

    python3 scripts/geocode_facilities.py            # geocode, update the register, write the review
    python3 scripts/geocode_facilities.py --offline  # re-apply the rules to the cache only

1. Only `name_status = confirmed` rows are geocoded as facilities; `to_confirm`
   rows get at most a town point.
2. OpenStreetMap Nominatim, jsonv2 + addressdetails + countrycodes, a
   descriptive User-Agent, at most one request per second. Every response is
   cached in data/geocode_cache.json and never asked for twice.
3. A result is a facility point only when ALL hold: the OSM object is
   amenity=hospital|clinic|doctors or carries healthcare=*; its name matches the
   register name (case- and accent-insensitive, Hospital/Hopital/Hospital Rural
   variants allowed); it lies in the register's admin1 region.
4. Otherwise a town point (place=city|town|village|hamlet|suburb), then stop.
   Never a district or country centroid.
5. geo_source = the OSM URL. geo_checked = "auto" only for a facility point
   that passed every rule in 3 (the default taken for this run, see
   docs/refinement/RUN_LOG.md); a person may set "yes". Everything else is
   left empty and appears as "location to confirm".
6. data/geocode_review.csv: one row per facility for human review.

Known traps (protocol): Zambia "Chipata District Hospital" (Q-ZMB-02) is not
geocoded until confirmed.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
REGISTER = os.path.join(ROOT, "data", "reference", "facility_register.csv")
CACHE = os.path.join(ROOT, "data", "geocode_cache.json")
REVIEW = os.path.join(ROOT, "data", "geocode_review.csv")
USER_AGENT = ("PEN-Plus regional dashboard facility geocoding (WHO AFRO NCD); "
              "one-off, cached, 1 req/s; contact via the WHO AFRO NCD programme")
ISO2 = {"BFA": "bf", "CMR": "cm", "COD": "cd", "COG": "cg", "ETH": "et", "KEN": "ke",
        "LBR": "lr", "MOZ": "mz", "NGA": "ng", "RWA": "rw", "SLE": "sl", "TZA": "tz",
        "UGA": "ug", "ZMB": "zm", "ZWE": "zw"}
#: Facilities the protocol says not to geocode until a query is answered.
DO_NOT_GEOCODE = {"ZMB-0002": "Q-ZMB-02: Chipata is both a Lusaka first-level hospital and a"
                              " town in Eastern Province"}
HEALTH_TYPES = {"hospital", "clinic", "doctors"}
PLACE_TYPES = {"city", "town", "village", "hamlet", "suburb"}
#: Words that say what kind of facility it is, not which one: removed before
#: comparing names, so "Hopital de District de Mfou" matches "Mfou District Hospital".
GENERIC = {"hospital", "hopital", "rural", "de", "du", "la", "le", "of", "the", "district",
           "general", "government", "regional", "provincial", "memorial", "level", "one", "1",
           "sub", "county", "health", "centre", "center", "primary", "lutheran", "christian",
           "referral", "hosp"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def distinctive(name: str) -> set[str]:
    return {t for t in norm(name).split() if t not in GENERIC}


def name_matches(register_name: str, osm_name: str) -> bool:
    """Both names must carry the same distinctive words. 'Chibombo District
    Hospital (Mwachisompola)' also matches an OSM name carrying either one."""
    reg = distinctive(re.sub(r"\(.*?\)", "", register_name))
    alt = distinctive(" ".join(re.findall(r"\((.*?)\)", register_name)))
    osm = distinctive(osm_name)
    return bool(osm) and (osm == reg or (alt and osm == alt) or (reg and osm == reg | alt))


ADMIN_WORDS = {"province", "region", "state", "territory", "capital", "district", "county"}


def in_region(result: dict, region: str, district: str = "") -> bool:
    """Inside the register's admin1 region: OSM's state / region names it, or
    names the register's own admin2 district, which lies inside that region
    (OpenStreetMap files Sierra Leone's hospitals under "Kono District", not
    "Eastern Province")."""
    addr = result.get("address") or {}
    for area in (region, district):
        target = distinctive(area) - ADMIN_WORDS
        if not target:
            continue
        for key in ("state", "region", "province", "county", "state_district"):
            got = distinctive(addr.get(key, "")) - ADMIN_WORDS
            if got and (target <= got or got <= target):
                return True
    return False


def is_health_facility(result: dict) -> bool:
    if result.get("category") == "amenity" and result.get("type") in HEALTH_TYPES:
        return True
    return bool((result.get("extratags") or {}).get("healthcare")) or \
        result.get("category") == "healthcare"


def osm_url(result: dict) -> str | None:
    t, i = result.get("osm_type"), result.get("osm_id")
    return f"https://www.openstreetmap.org/{t}/{i}" if t and i else None


def km(a, b) -> float:
    (la1, lo1), (la2, lo2) = a, b
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2 +
         math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(h))


class Nominatim:
    def __init__(self, offline: bool):
        self.offline = offline
        self.cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
        self.last = 0.0
        self.requests = 0

    def search(self, q: str, iso2: str) -> list[dict]:
        params = {"q": q, "format": "jsonv2", "addressdetails": 1, "extratags": 1,
                  "countrycodes": iso2, "limit": 5}
        key = urllib.parse.urlencode(params)
        if key in self.cache:
            return self.cache[key]
        if self.offline:
            return []
        wait = 1.05 - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request("https://nominatim.openstreetmap.org/search?" + key,
                                     headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        self.last = time.time()
        self.requests += 1
        self.cache[key] = data
        return data

    def save(self):
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=0, sort_keys=True)


def geocode(row: dict, nom: Nominatim) -> dict:
    iso2 = ISO2.get(row["iso3"])
    out = {"latitude": "", "longitude": "", "geo_precision": "", "geo_source": "",
           "geo_checked": "", "osm_name": "", "km_to_town": "", "reason": ""}
    if row["facility_id"] in DO_NOT_GEOCODE:
        out["reason"] = "not geocoded: " + DO_NOT_GEOCODE[row["facility_id"]]
        return out
    if not iso2:
        out["reason"] = "no country code"
        return out

    town_point = None
    if row["town"]:
        query = ", ".join(x for x in (row["town"], row["admin1_region"], row["country"]) if x)
        for res in nom.search(query, iso2):
            if res.get("category") == "place" and res.get("type") in PLACE_TYPES:
                town_point = res
                break

    if row["name_status"] == "confirmed":
        for q in (row["geocode_query"], row["facility_name"]):
            for res in nom.search(q, iso2):
                checks = (is_health_facility(res),
                          name_matches(row["facility_name"], res.get("name") or ""),
                          in_region(res, row["admin1_region"], row["admin2_district"])
                          if row["admin1_region"] else False)
                if all(checks):
                    lat, lon = float(res["lat"]), float(res["lon"])
                    out.update(latitude=f"{lat:.6f}", longitude=f"{lon:.6f}",
                               geo_precision="facility", geo_source=osm_url(res) or "",
                               geo_checked="auto", osm_name=res.get("name") or "",
                               reason="facility: OSM health facility, name and region match")
                    if town_point:
                        out["km_to_town"] = f"{km((lat, lon), (float(town_point['lat']), float(town_point['lon']))):.1f}"
                    return out
        out["reason"] = "no OSM object passed all three facility rules"
    else:
        out["reason"] = "facility name to confirm: town point at most"

    if town_point:
        out.update(latitude=f"{float(town_point['lat']):.6f}",
                   longitude=f"{float(town_point['lon']):.6f}", geo_precision="town",
                   geo_source=osm_url(town_point) or "", osm_name=town_point.get("name") or "",
                   km_to_town="0.0")
        out["reason"] += "; town point (not shown on the map until checked)"
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="use the cache only")
    a = ap.parse_args()
    with open(REGISTER, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    nom = Nominatim(a.offline)
    review = []
    try:
        for row in rows:
            if row.get("geo_checked") == "yes":        # a person's check is never overwritten
                review.append({**row, "osm_name": "", "km_to_town": "", "reason": "checked by a person"})
                continue
            g = geocode(row, nom)
            for k in ("latitude", "longitude", "geo_precision", "geo_source", "geo_checked"):
                row[k] = g[k]
            review.append({**row, **g})
            print(f"{row['facility_id']:9s} {g['geo_precision'] or '-':9s} {g['geo_checked'] or '-':5s}"
                  f" {row['facility_name'][:40]:40s} {g['reason']}")
    finally:
        nom.save()
    with open(REGISTER, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(REVIEW, "w", encoding="utf-8", newline="") as f:
        cols = ["facility_id", "country", "facility_name", "name_status", "status", "osm_name",
                "geo_precision", "km_to_town", "geo_checked", "latitude", "longitude",
                "geo_source", "reason"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(review)
    auto = sum(1 for r in rows if r["geo_checked"] == "auto")
    town = sum(1 for r in rows if r["geo_precision"] == "town")
    print(f"\n{nom.requests} Nominatim requests; {auto} facility points (geo_checked=auto),"
          f" {town} town points, {len(rows) - auto} listed as location to confirm."
          f"\nReview: {os.path.relpath(REVIEW, ROOT)}")


if __name__ == "__main__":
    main()
