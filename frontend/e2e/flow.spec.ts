import { test, expect } from "@playwright/test";
import { registerAccount } from "./helpers";

test.beforeEach(async ({ page }) => {
  // 自动测试不访问外部 TTS 服务；文字交互仍按真实页面流程执行。
  await page.route("**/api/v1/tts", (route) => route.fulfill({ status: 204 }));
});

test.describe("已登录流程", () => {
  test.beforeEach(async ({ page }) => {
    await registerAccount(page);
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
  await page.getByRole("button", { name: "注册账号" }).click();
  await page.getByLabel("邀请码").fill("WRONG");
  await page.getByLabel("用户名").fill("wrong_invite_user");
  await page.getByLabel("密码", { exact: true }).fill("Password123");
  await page.getByLabel("确认密码").fill("Password123");
  await page.getByRole("button", { name: "注册并进入" }).click();
  await expect(page.getByText("邀请码无效、已过期或已用完")).toBeVisible();
});

test("无效登录凭证会被后端拒绝并返回登录页", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("sb_token", "invalid-or-expired-token");
  });
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);
});
