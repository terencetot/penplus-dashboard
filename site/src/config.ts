/**
 * Site configuration switches. Changing one is a code-free decision the team
 * takes, recorded in docs/refinement/RUN_LOG.md.
 */

/**
 * National coats of arms on the country profile header. Off until WHO AFRO
 * communications confirms they may appear on a public WHO dashboard
 * (docs/refinement/05_design/COUNTRY_ASSETS.md). Off means nothing is shown
 * and nothing is fetched.
 */
export const SHOW_COAT_OF_ARMS = false;

/**
 * Country identity files present under site/public/assets/countries/<ISO3>/
 * (map.svg or map.png, arms.png). Listed here rather than probed, so a
 * missing file never costs a failed request: add an entry when a file is
 * dropped in. A country without a map falls back to its ISO3 tile; without
 * arms, to nothing.
 */
export const COUNTRY_ASSETS: Record<string, { map?: string; arms?: string }> = {};
