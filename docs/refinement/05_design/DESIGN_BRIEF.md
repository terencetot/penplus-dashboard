# Design brief: the PEN-Plus identity

This is the **PEN-Plus regional dashboard**. ICPPA 2026 was the conference's branding and is **not** used here
(no ICPPA ribbon, colours or logo). The ICPPA country presentations are only a data source.

## Keep what the site already has
The current site (`site/src/styles/tokens.css`) already carries a coherent PEN-Plus system, shared with the
NCD Surveillance Intelligence Platform: WHO institutional navy scale, one accent `#E8743B` (gap to milestone and alerts only),
neutral greys, Schibsted Grotesk self-hosted, light mode. Keep it. The changes below refine it; they don't replace it.

## Additions (`tokens.penplus.additions.css`)
1. **Condition colours** (charts only, never performance): T1D `#016294`, SCD `#C8102E`, RHD `#6B4FA0`,
   other / not split `#8792A8`. Always with a legend or direct label.
2. **Cohort colours**: first HCT round `--navy-800`, second HCT round `--navy-300` (with outline).
3. **Provenance marks**: one consistent chip for *Historical (ICPPA 2026 country presentations)*,
   *Validated return*, *Held* (accent outline), *No return yet* (dashed). Every figure shows one of them.
4. **Value-type labels** next to patient figures: "ever enrolled", "active in care", "as of <date>".
5. **Status vocabulary** unchanged (met / partly met / not met / not reported), each with icon and word.

## Country identity (new, Country profile screen)
The team has country maps (coloured, as used on the country posters) and national coats of arms.
See `COUNTRY_ASSETS.md` for file names and placement. In short: the Country profile header shows the
country map on the left, the name and cohort chips in the middle, the coat of arms small on the right;
the Facilities map reuses the country map as an inset when one country is filtered.

**Check first with WHO AFRO communications** that national coats of arms may appear on a public WHO dashboard
(they were used on meeting posters; a public website can follow different rules). Build them behind a
configuration flag so they can be switched off without a code change.

## Facility map (Facilities screen)
- One point per facility from `02_data/facility_register.csv` once geocoded and checked; shape and label by status
  (active / partial / planned / to confirm). Never sized or coloured by performance.
- WHO-cleared boundaries, the standard WHO map disclaimer under the map.
- Order on the screen: KPI row, then map, then register table (CLAUDE.md: no map as the first element).
- Popup: facility name, district, partner, conditions, the patient figure printed on the slide (if any) with its source.

## The 3D hero
Keep the isometric tile hero on the overview (decorative; encodes cohort only, uniform height). When the
country maps are in, the tiles can use them as silhouettes.
