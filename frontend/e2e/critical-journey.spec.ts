import { expect, test, type BrowserContext } from "@playwright/test";

test.skip(!process.env.FULL_STACK_E2E, "requires the isolated Compose full stack");

const cookiePath = (token: string) => `/api/projects/by-token/${token}`;

async function expectHardenedCookie(
  context: BrowserContext,
  name: "travel_creator" | "travel_voter",
  token: string,
) {
  const cookie = (await context.cookies()).find(
    (item) => item.name === name && item.path === cookiePath(token),
  );
  expect(cookie, `${name} must be stored by the real HTTPS response`).toBeDefined();
  expect(cookie).toMatchObject({
    name,
    domain: "localhost",
    path: cookiePath(token),
    httpOnly: true,
    secure: true,
    sameSite: "Lax",
  });
}

test("real stack: create, recover, vote, reveal, rotate, delete and recover", async ({
  context,
  page,
  request,
}) => {
  const rejected = await request.post("/api/projects", {
    headers: { Origin: "https://invalid.example" },
    data: { destination: "Should Not Persist", duration_days: 1, departure: "Nowhere" },
  });
  expect(rejected.status()).toBe(403);

  await page.goto("/");
  await page.getByLabel("目的地 *").fill("Kyoto E2E");
  await page.getByLabel("出发地 *").fill("Shanghai E2E");
  await page.getByLabel("行程天数 *").fill("3");
  await page.getByRole("button", { name: "创建行程方案" }).click();

  const recoveryPanel = page.getByLabel("恢复密钥");
  await expect(recoveryPanel).toBeVisible();
  const recoveryKey = (await recoveryPanel.locator("code").textContent())?.trim();
  expect(recoveryKey).toBeTruthy();
  const shareUrl = await page.locator("input[readonly]").inputValue();
  const originalToken = shareUrl.split("/p/").at(-1)!;
  expect(originalToken).toBeTruthy();
  await expectHardenedCookie(context, "travel_creator", originalToken);

  await page.getByRole("button", { name: /查看报告/ }).click();
  await expect(page).toHaveURL(new RegExp(`/p/${originalToken}$`));
  await expect(page.getByRole("heading", { name: "Kyoto E2E" })).toBeVisible();

  await context.clearCookies();
  await page.reload();
  await expect(page.getByText("创建者凭证需要恢复")).toBeVisible();
  await page.getByLabel("恢复密钥").fill(recoveryKey!);
  await page.getByRole("button", { name: "恢复创建者权限" }).click();
  await expect(page.getByText("手工添加地点")).toBeVisible();
  await expectHardenedCookie(context, "travel_creator", originalToken);

  await page.getByLabel("地点名称（必填）").fill("伏见稻荷 E2E");
  await page.getByRole("button", { name: "添加", exact: true }).click();
  await page.getByRole("button", { name: "重要", exact: true }).click();
  await expect(page.getByText("伏见稻荷 E2E")).toBeVisible();
  await page.getByRole("button", { name: "想去", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "想去", exact: true, pressed: true }),
  ).toBeVisible();
  await expectHardenedCookie(context, "travel_voter", originalToken);

  await page.getByRole("button", { name: "公开汇总" }).click();
  await expect(page.getByText("当前公开匿名汇总。")).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "重要", exact: true }).click();
  await expect(page.getByRole("button", { name: "想去 (1)", pressed: true })).toBeVisible();

  await page.getByRole("button", { name: "重新隐藏" }).click();
  await expect(page.getByText(/当前隐藏汇总/)).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "重要", exact: true }).click();
  await expect(page.getByText("伏见稻荷 E2E")).toBeVisible();
  await expect(page.getByRole("button", { name: "想去", exact: true, pressed: true })).toBeVisible();

  await page.getByRole("button", { name: "轮换分享链接" }).click();
  await expect(page).not.toHaveURL(new RegExp(`/p/${originalToken}$`));
  const rotatedToken = new URL(page.url()).pathname.split("/p/").at(-1)!;
  expect(rotatedToken).toBeTruthy();
  await expectHardenedCookie(context, "travel_creator", rotatedToken);
  await page.reload();
  await page.getByRole("button", { name: "重要", exact: true }).click();
  await expect(page.getByText("伏见稻荷 E2E")).toBeVisible();

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "删除项目" }).click();
  await page.goto(`/p/${rotatedToken}`);
  await expect(page.getByText("无法加载报告")).toBeVisible();
  await page.getByLabel("恢复密钥").fill(recoveryKey!);
  await page.getByRole("button", { name: "恢复创建者权限" }).click();
  await expect(page).not.toHaveURL(new RegExp(`/p/${rotatedToken}$`));
  const recoveredToken = new URL(page.url()).pathname.split("/p/").at(-1)!;
  expect(recoveredToken).toBeTruthy();
  await expectHardenedCookie(context, "travel_creator", recoveredToken);
  await expect(page.getByRole("heading", { name: "Kyoto E2E" })).toBeVisible();
  await page.getByRole("button", { name: "重要", exact: true }).click();
  await expect(page.getByText("伏见稻荷 E2E")).toBeVisible();
});
