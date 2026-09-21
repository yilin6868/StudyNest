import { expect, test } from "@playwright/test";
import { registerAccount } from "./helpers";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/tts", (route) => route.fulfill({ status: 204 }));
  await registerAccount(page);
});

test("刷新后恢复当前会话，新对话不带入旧消息", async ({ page }) => {
  const text = `今天先复习英语 ${Date.now()}`;
  await page.getByPlaceholder("和搭子说句话…").fill(text);
  await page.getByLabel("发送").click();
  await expect(page.getByText(text)).toBeVisible();
  await expect.poll(() => page.evaluate(() => localStorage.getItem("sb_chat_session"))).not.toBeNull();

  await page.reload();
  const userBubble = page.locator("div.self-end").filter({ hasText: text });
  await expect(userBubble).toBeVisible();

  await page.getByText("最近对话").click();
  await page.getByRole("button", { name: "＋ 新对话" }).click();
  await expect(userBubble).not.toBeVisible();
  await expect(page.getByText("新对话已准备好。")).toBeVisible();
});

test("用户可以保存并删除白名单学习记忆", async ({ page }) => {
  await page.getByRole("link", { name: "我的" }).click();
  const field = page.getByLabel("学习习惯");
  await field.fill("我一般晚上九点学习");
  const section = page.getByRole("heading", { name: "搭子记忆" }).locator("..");
  await section.getByRole("button", { name: "保存" }).first().click();
  await expect(page.getByText("已保存，小悟下次聊天会参考。")).toBeVisible();

  await page.reload();
  await expect(page.getByLabel("学习习惯")).toHaveValue("我一般晚上九点学习");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("heading", { name: "搭子记忆" }).locator("..").getByRole("button", { name: "删除" }).first().click();
  await expect(page.getByLabel("学习习惯")).toHaveValue("");
});

test("明显危机表达进入安全卡片且没有学习动作", async ({ page }) => {
  await page.getByPlaceholder("和搭子说句话…").fill("我不想活了");
  await page.getByLabel("发送").click();
  const safety = page.getByTestId("safety-message");
  await expect(safety).toBeVisible();
  await expect(safety).toContainText("请立即联系身边信任的人");
  await expect(page.getByTestId("agent-action-card")).toHaveCount(0);
});
