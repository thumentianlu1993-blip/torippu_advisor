import { expect, test } from "@playwright/test";

test.skip(!process.env.BRIDGE_SMOKE, "bridge matrix runs in its isolated CI script");

test("actual Next.js bootstrap renders through the read-only bridge", async ({ page }) => {
  await page.goto("/p/11111111-1111-1111-1111-111111111111");
  await expect(page.getByRole("heading", { name: "Legacy" })).toBeVisible();
  await expect(page.getByText("手工添加地点")).toHaveCount(0);
  await page.getByRole("button", { name: "重要", exact: true }).click();
  await expect(page.getByText("Legacy Spot")).toBeVisible();
  await expect(page.getByLabel("coverage status")).toBeVisible();
});
