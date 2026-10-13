import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const SCREENS = [
  "",
  "timeline",
  "evidence",
  "lab",
  "policies",
  "inspection",
  "plant",
  "replay",
  "method",
  "handover",
];
const COMBOS = [
  { lang: "en", theme: "light" },
  { lang: "ar", theme: "dark" },
  { lang: "ar", theme: "light" },
  { lang: "en", theme: "dark" },
] as const;

async function prepare(page: Page, lang: string, theme: string) {
  await page.addInitScript(
    (args: { l: string; t: string }) => {
      window.localStorage.setItem("madkhal.lang", args.l);
      window.localStorage.setItem("madkhal.theme", args.t);
    },
    { l: lang, t: theme },
  );
}

async function settle(page: Page) {
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("status").filter({ hasText: /Loading|جارٍ التحميل/ })).toHaveCount(
    0,
    { timeout: 30_000 },
  );
}

for (const c of COMBOS) {
  for (const s of SCREENS) {
    test(`MK-L8-008 axe finds no violations on /${s || "console"} (${c.lang}, ${c.theme})`, async ({
      page,
      baseURL,
    }) => {
      test.setTimeout(180_000); // axe on the long timeline ribbon can be slow on a loaded machine
      await prepare(page, c.lang, c.theme);
      const requests: string[] = [];
      page.on("request", (r) => requests.push(r.url()));
      const errors: string[] = [];
      page.on("console", (m) => {
        if (m.type() === "error") errors.push(m.text());
      });
      page.on("pageerror", (e) => errors.push(e.message));
      await page.goto(`/#/${s}`);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.getByTestId("banner")).toBeVisible();
      await settle(page);
      await expect(page.locator("html")).toHaveAttribute("dir", c.lang === "ar" ? "rtl" : "ltr");
      // @axe-core/playwright ships its own playwright-core types; the page object is compatible
      type AxePage = ConstructorParameters<typeof AxeBuilder>[0]["page"];
      const results = await new AxeBuilder({ page: page as unknown as AxePage })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
        .analyze();
      const summary = results.violations.map(
        (v) =>
          `${v.id}: ${v.nodes
            .slice(0, 3)
            .map((n) => n.target.join(" "))
            .join(", ")}`,
      );
      expect(summary).toEqual([]);
      expect(errors).toEqual([]);
      expect(
        requests.filter((u) => !u.startsWith(`${baseURL}/`) && !u.startsWith(`blob:${baseURL}/`)),
      ).toEqual([]);
    });
  }
}

test("MK-L8-004 keyboard reaches navigation and settings with visible focus", async ({ page }) => {
  await page.goto("/#/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  for (let i = 0; i < 4; i += 1) await page.keyboard.press("Tab");
  const outline = await page.evaluate(
    () => getComputedStyle(document.activeElement as Element).outlineStyle,
  );
  expect(outline).not.toBe("none");
});

const WIDTHS = [1440, 1024, 768];
test("design QA screenshots", async ({ browser, baseURL }) => {
  test.setTimeout(1_500_000);
  for (const c of COMBOS) {
    for (const w of WIDTHS) {
      // a fresh context per combination so stored settings cannot leak between them
      const ctx = await browser.newContext({ baseURL, viewport: { width: w, height: 1000 } });
      const page = await ctx.newPage();
      await prepare(page, c.lang, c.theme);
      for (const s of SCREENS) {
        await page.goto(`/#/${s}`);
        await settle(page);
        await expect(page.locator("html")).toHaveAttribute("dir", c.lang === "ar" ? "rtl" : "ltr");
        await page.waitForTimeout(s === "inspection" ? 6000 : 300);
        await page.screenshot({
          path: `test-results/qa/${c.lang}-${c.theme}-${w}-${s || "console"}.png`,
          fullPage: true,
        });
      }
      await ctx.close();
    }
  }
});
