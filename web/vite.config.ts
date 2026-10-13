/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Live mode proxies /v1 to the local API (madkhal serve). Static mode reads the JSON files
// written by `madkhal snapshot` into public/api, so it needs no backend at all.
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: "./",
  define: {
    __MADKHAL_MODE__: JSON.stringify(mode === "static" ? "static" : "live"),
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/v1": "http://127.0.0.1:8000" },
  },
  build: { outDir: "dist", sourcemap: false, chunkSizeWarningLimit: 1200 },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
}));
