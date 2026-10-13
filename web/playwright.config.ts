import { defineConfig, devices } from "@playwright/test";

// Set MADKHAL_E2E_URL to test an already running server (for example the live mode build).
const external = process.env.MADKHAL_E2E_URL;

// A dedicated port, never reused, so another local preview server cannot be tested by mistake.
// End to end tests run against the static demo build (npm run build:static after
// `madkhal snapshot`), served by `vite preview`. No backend is needed.
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: external ?? "http://127.0.0.1:4317",
    trace: "off",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: external
    ? undefined
    : {
        command: "npx vite preview --port 4317 --strictPort --host 127.0.0.1",
        url: "http://127.0.0.1:4317",
        reuseExistingServer: false,
        timeout: 60_000,
      },
});
