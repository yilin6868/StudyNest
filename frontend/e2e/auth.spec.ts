import { test, expect, type Page } from "@playwright/test";
import { registerAccount } from "./helpers";

async function login(page: Page) {
  await registerAccount(page);
}

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/tts", (route) => route.fulfill({ status: 204 }));
});

test("校验登录期间不显示受保护内容", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("sb_token", "invalid-token"));
  await page.route("**/api/v1/auth/session", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 400));
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: "HTTP_401", message: "登录已过期" } }),
    });
  });

  await page.goto("/");
  await expect(page.getByText("正在确认登录状态…")).toBeVisible();
  await expect(page.getByRole("navigation")).toHaveCount(0);
  await expect(page).toHaveURL(/\/login/);
});

test("网络错误保留 Token 并提供重试", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("sb_token", "keep-on-network-error"));
  await page.route("**/api/v1/auth/session", (route) => route.abort("failed"));
  await page.goto("/");

  await expect(page.getByText("暂时无法确认登录状态，请检查网络后重试。")).toBeVisible();
  await expect(page.getByRole("button", { name: "重新检查" })).toBeVisible();
  await expect(page.getByRole("navigation")).toHaveCount(0);
  expect(await page.evaluate(() => localStorage.getItem("sb_token"))).toBe(
    "keep-on-network-error",
  );
});

test("退出登录后受保护页面不可访问", async ({ page }) => {
  await login(page);
  const oldToken = await page.evaluate(() => localStorage.getItem("sb_token"));
  await page.getByRole("link", { name: "我的" }).click();
  await page.getByRole("button", { name: "退出登录" }).click();

  await expect(page).toHaveURL(/\/login/);
  expect(await page.evaluate(() => localStorage.getItem("sb_token"))).toBeNull();
  await page.evaluate((token) => localStorage.setItem("sb_token", token ?? ""), oldToken);
  await page.goto("/focus");
  await expect(page).toHaveURL(/\/login/);
});

test("注册后可以使用用户名和密码重新登录", async ({ page }) => {
  const username = await registerAccount(page);
  await page.getByRole("link", { name: "我的" }).click();
  await page.getByRole("button", { name: "退出登录" }).click();
  await page.getByRole("button", { name: "已有账号" }).click();
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码", { exact: true }).fill("Password123");
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page.getByText("小悟").first()).toBeVisible();
});
