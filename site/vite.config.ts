import { defineConfig } from "vite";
import { resolve } from "node:path";

// Static build only: no SSR, no dev-only API routes. The output of `vite build`
// is plain HTML/CSS/JS that can be served from any file host, per the
// specification's architecture rule "no build server required in production".
export default defineConfig({
  base: "./",
  resolve: {
    alias: { "@": resolve(__dirname, "src") },
  },
  build: {
    target: "es2022",
    sourcemap: true,
    rollupOptions: {
      output: {
        // Stable, cacheable chart-vendor chunk separate from screen code.
        manualChunks: {
          plot: ["@observablehq/plot"],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
  },
});
