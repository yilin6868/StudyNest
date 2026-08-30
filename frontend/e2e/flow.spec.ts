import { test, expect } from "@playwright/test";

test.describe("已登录流程", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.getByPlaceholder("邀请码").fill("DEMO123");
    await page.getByRole("button", { name: "进入自习室" }).click();
    await expect(page.getByText("小悟").first()).toBeVisible();
  });

  test("核心闭环：聊天 → 专注 → 我的", async ({ page }) => {
    await page.getByPlaceholder("和搭子说句话…").fill("你好");
    await page.getByLabel("发送").click();
    await expect(page.locator(".self-end").first()).toBeVisible();
    await expect(page.locator(".self-start").first()).toBeVisible({ timeout: 20_000 });

    await page.getByRole("link", { name: "专注" }).click();
    await expect(page.getByRole("button", { name: "开始专注" })).toBeVisible();
    await page.getByRole("button", { name: "开始专注" }).click();
    await expect(page.getByRole("button", { name: "暂停" })).toBeVisible();

    await page.getByRole("link", { name: "我的" }).click();
    await expect(page.getByText("累计番茄")).toBeVisible();
    await expect(page.getByText("累计时长")).toBeVisible();
  });
});

test("未登录访问首页跳转登录页", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);
});

test("错误邀请码被拒", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("邀请码").fill("WRONG");
  await page.getByRole("button", { name: "进入自习室" }).click();
  await expect(page.getByText("邀请码无效")).toBeVisible();
});
