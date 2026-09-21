/**
 * Demo mode loads pipeline/tools/generate_demo_bundle.py's synthetic output
 * (site/public/demo-data) instead of the real bundle, so the site can be
 * reviewed fully populated -- most real cells are NR today because no real
 * Phase Two return has been submitted yet, which is correct but makes the
 * design hard to judge. It is never the default: it must be turned on
 * explicitly, it persists only in this browser (localStorage), and every
 * screen shows a permanent banner while it is on. No demo number is ever
 * written into site/public/data or the real store.
 */
const STORAGE_KEY = "penplus.demoMode";

function fromQueryString(): boolean | null {
  const v = new URLSearchParams(location.search).get("demo");
  if (v === "1" || v === "true") return true;
  if (v === "0" || v === "false") return false;
  return null;
}

export function isDemoMode(): boolean {
  const fromQuery = fromQueryString();
  if (fromQuery !== null) {
    setDemoMode(fromQuery);
    return fromQuery;
  }
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

export function setDemoMode(on: boolean): void {
  try {
    if (on) localStorage.setItem(STORAGE_KEY, "1");
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* per-viewer convenience only */
  }
}
