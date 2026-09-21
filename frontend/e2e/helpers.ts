import { expect, type Page } from "@playwright/test";

const inviteCode = process.env.E2E_INVITE_CODE ?? "DEMO123";

export async function registerAccount(page: Page) {
  const username = `e2e_${Date.now()}_${Math.random().toString(16).slice(2, 10)}`;
  await page.goto("/login");
  await page.getByRole("button", { name: "注册账号" }).click();
  await page.getByLabel("邀请码").fill(inviteCode);
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码", { exact: true }).fill("Password123");
  await page.getByLabel("确认密码").fill("Password123");
  await page.getByRole("button", { name: "注册并进入" }).click();
  await expect(page.getByText("小悟").first()).toBeVisible();
  return username;
}
