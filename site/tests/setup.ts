import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, vi } from "vitest";

/**
 * Screens fetch the real bundle at runtime; tests stub `fetch` to read the
 * same files straight off disk from site/public/data, so the tests exercise
 * the actual pipeline output rather than a hand-written mock that could
 * drift from what export.py really produces.
 */
const DATA_DIR = resolve(__dirname, "../public/data");

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const path = url.replace(/^.*\/data\//, "");
      try {
        const body = readFileSync(resolve(DATA_DIR, path), "utf-8");
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
