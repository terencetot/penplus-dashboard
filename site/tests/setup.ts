import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, vi } from "vitest";

/**
 * Screens fetch the real bundle at runtime; tests stub `fetch` to read the
 * same files straight off disk from site/public/data (or site/public/demo-data
 * for a test that turns demo mode on), so the tests exercise the actual
 * pipeline output rather than a hand-written mock that could drift from what
 * export.py really produces.
 */
const REAL_DIR = resolve(__dirname, "../public/data");
const DEMO_DIR = resolve(__dirname, "../public/demo-data");

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      // lib/bundle.ts's dataRoot() serves "demo-data/" or "data/" -- match
      // the optional "demo-" prefix so both resolve to the right directory,
      // not just the real one (a plain `/data/` match would also fire
      // partway through "demo-data/", picking the wrong directory).
      const isDemo = /\/demo-data\//.test(url);
      const path = url.replace(/^.*\/(?:demo-)?data\//, "");
      try {
        const body = readFileSync(resolve(isDemo ? DEMO_DIR : REAL_DIR, path), "utf-8");
        return new Response(body, { status: 200 });
      } catch {
        return new Response("not found", { status: 404 });
      }
    }),
  );
  // Each test gets an isolated localStorage-like store via jsdom's own
  // window.localStorage; only the bundle cache module keeps in-memory state
  // across tests, so reset the module registry per test file where needed.
});
