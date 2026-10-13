import { expect, test } from "@playwright/test";

const SCREENS = [
  { path: "/#/", heading: "Console" },
  { path: "/#/evidence", heading: "Evidence" },
];

for (const s of SCREENS) {
  test(`MK-L8-010 renders ${s.heading} with no request outside its own origin`, async ({
    page,
    baseURL,
  }) => {
    const requests: string[] = [];
    page.on("request", (r) => requests.push(r.url()));
    await page.goto(s.path);
    await expect(page.getByRole("heading", { level: 1, name: s.heading })).toBeVisible();
    await expect(page.getByTestId("banner")).toContainText(
      "Evidence: real satellite history from the Nadhir hindcast.",
    );
    await page.waitForLoadState("networkidle");
    const external = requests.filter((u) => !u.startsWith(`${baseURL}/`));
    expect(external).toEqual([]);
  });
}

test("MK-L8-001 console tiles show belief intervals from the static snapshot", async ({ page }) => {
  await page.goto("/#/");
  for (const id of ["kalba", "barka", "alraha"]) {
    await expect(page.getByTestId(`tile-${id}`)).toBeVisible();
  }
  await expect(page.getByTestId("tile-kalba").getByRole("img").first()).toHaveAttribute(
    "aria-label",
    /median/,
  );
  await page.screenshot({ path: "test-results/p4-console.png", fullPage: true });
});

test("MK-L8-001 evidence screen shows the calendar and the counted track record", async ({
  page,
}) => {
  await page.goto("/#/evidence");
  await expect(page.getByText(/caught 1 of 3 observable dated events/)).toBeVisible();
  await expect(page.getByRole("img", { name: /Coverage calendar/ })).toBeVisible();
  await page.screenshot({ path: "test-results/p4-evidence.png", fullPage: true });
});

test("MK-L8-002 banner stays visible in Arabic", async ({ page }) => {
  await page.goto("/#/");
  await page.getByRole("button", { name: "Switch to Arabic" }).click();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByTestId("banner")).toContainText("الأدلة");
  await page.screenshot({ path: "test-results/p4-console-ar.png", fullPage: true });
});
