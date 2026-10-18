# Country maps and coats of arms

## Where to put them
```
site/public/assets/countries/<ISO3>/map.svg     (or map.png, transparent background, at least 600 px wide)
site/public/assets/countries/<ISO3>/arms.png    (transparent background, at least 200 px high)
```
ISO3 codes as in `pipeline/src/penplus_pipeline/common.py` (AGO, BEN, BWA, BFA, BDI, CPV, CMR, COD, COG, SWZ, ETH,
GAB, GMB, GHA, KEN, LSO, LBR, MWI, MLI, MOZ, NER, NGA, RWA, SEN, SLE, SSD, TGO, TZA, UGA, ZMB, ZWE). One folder per
country; a missing file is allowed.

## How the site uses them
- **Country profile header**: map on the left (`--country-map-size`), country name and chips (cohort, phase, provenance)
  in the middle, coat of arms on the right (`--country-arms-size`). Missing map: the ISO3 tile used today. Missing arms: nothing.
- **Facilities screen**: when one country is filtered, its map is the inset behind the facility points.
- **Overview hero**: optional later, the maps as tile silhouettes.
- `alt` text: "Map of <country>" / "Coat of arms of <country>".
- A configuration flag `SHOW_COAT_OF_ARMS` (default as the team decides after checking with communications).

## Before publishing
Confirm with WHO AFRO communications that the coloured maps follow WHO-cleared boundaries and that national
coats of arms may appear on a public WHO dashboard.
