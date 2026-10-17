# Geocoding the facility register

`facility_register.csv` lists 43 facilities and pilot sites named in the ICPPA 2026 decks
(34 with a confirmed facility name, 9 where only the district or town is known). Latitude and longitude are empty:
they must be found and checked, never guessed.

## Method (run on a machine with internet access)
1. Only rows with `name_status = confirmed` are geocoded as facilities. Rows `to_confirm` get at most a **town**
   point, flagged as such, until the WHO Country Office gives the facility name.
2. Query OpenStreetMap Nominatim with `geocode_query` (`format=jsonv2&addressdetails=1&countrycodes=<iso2>`),
   with a descriptive User-Agent and **at most 1 request per second** (Nominatim usage policy). Cache every response
   in `data/geocode_cache.json` so the script never queries twice.
3. Accept a result as `geo_precision = facility` only when **all** of these hold:
   - the OSM object is `amenity=hospital|clinic|doctors` or `healthcare=*`;
   - its name matches the facility name (case- and accent-insensitive, allowing "Hospital/Hôpital/Hospital Rural" variants);
   - it lies inside the stated `admin1_region` (check `address.state` / `address.region`).
4. Otherwise fall back to the town (`geo_precision = town`), then stop. Never use a district or country centroid for a facility.
5. Fill `geo_source` with the OSM URL (`https://www.openstreetmap.org/<type>/<id>`) and leave `geo_checked` empty.
6. Write a review table `data/geocode_review.csv` (name, chosen OSM name, distance to town centre, precision) and
   show it to the user. Only after the user marks `geo_checked = yes` does a point appear on the public map.

## Known traps
- **Zambia, "Chipata District Hospital"** (Q-ZMB-02): Chipata is both a first-level hospital in Lusaka and a town in
  Eastern Province. Do not geocode until confirmed.
- **Chibombo District Hospital (Mwachisompola)**: the NCDI table names both; OSM may know only one of the two names.
- **Liberia, Phebe / C.B. Dunbar / Tellewoyan**: confirmed hospital names, but their PEN-Plus clinic status is open (Q-LBR-03): map them as `status = to_confirm`.
- **Rwanda**: national coverage (45 hospitals). The register holds only the three first sites named in the deck; ask the MoH for the full list rather than mapping a partial set as if it were complete.

## Longer term
Ask that Annex A of the reporting tool carry latitude/longitude or the DHIS2 organisation-unit UID. With the
UID, coordinates come straight from each country's DHIS2 and no name matching is needed.
