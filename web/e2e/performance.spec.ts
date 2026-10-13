import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(HERE, "..", "..", "results", "performance_web.json");
const BUDGET_S = 3;
const RUNS = 5;

test("MK-X-009 static demo first load shows the console within 3 seconds", async ({
  browser,
  baseURL,
}) => {
  test.skip(Boolean(process.env.MADKHAL_E2E_URL), "the budget is for the static demo");
  const seconds: number[] = [];
  for (let i = 0; i < RUNS; i += 1) {
    // a fresh context per run: nothing cached from the previous load
    const ctx = await browser.newContext({ baseURL });
    const page = await ctx.newPage();
    const t0 = Date.now();
    await page.goto("/#/");
    await expect(page.getByTestId("banner")).toBeVisible();
    await expect(page.getByTestId("tile-kalba")).toBeVisible();
    seconds.push((Date.now() - t0) / 1000);
    await ctx.close();
  }
  const max = Math.max(...seconds);
  writeFileSync(
    OUT,
    `${JSON.stringify(
      {
        measure:
          "Seconds from navigation to the banner and the first site tile being visible, static build served by vite preview on the same machine, fresh browser context per run.",
        runs: RUNS,
        seconds: seconds.map((s) => Math.round(s * 1000) / 1000),
        max: Math.round(max * 1000) / 1000,
        budget_s: BUDGET_S,
      },
      null,
      2,
    )}\n`,
    "utf-8",
  );
  expect(max).toBeLessThan(BUDGET_S);
});
