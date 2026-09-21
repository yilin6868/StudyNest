import { test, expect } from "@playwright/test";
import { registerAccount } from "./helpers";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/tts", (route) => route.fulfill({ status: 204 }));
  await registerAccount(page);
});

test("今日目标在聊天页保存后会同步到专注页", async ({ page }) => {
  const goal = page.getByRole("region", { name: "今日目标" });
  await goal.getByPlaceholder("今天准备完成什么？").fill("背 30 个单词");
  await goal.getByRole("button", { name: "保存", exact: true }).click();
  await expect(goal.getByText("已保存")).toBeVisible();

  await page.getByRole("link", { name: "专注" }).click();
  await expect(page.getByRole("region", { name: "今日目标" }).getByText("背 30 个单词")).toBeVisible();
});

test("AI 提议的开始动作必须确认后才写入计时器", async ({ page }) => {
  const token = "test-confirmation-token-12345678901234567890";
  await page.route("**/api/v1/chat", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        protocolVersion: "1.2",
        requestId: "req_test_action",
        sessionId: "00000000-0000-4000-8000-000000000001",
        reply: "要开始一轮 30 分钟专注吗？",
        source: "llm",
        responseMode: "normal",
        actions: [
          {
            type: "confirm_start_focus",
            durationMinutes: 30,
            confirmationToken: token,
            expiresAt: new Date(Date.now() + 60_000).toISOString(),
          },
        ],
      }),
    }),
  );
  await page.route("**/api/v1/agent/actions/resolve", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        accepted: true,
        action: { type: "start_focus", durationMinutes: 30 },
        message: "已确认开始专注",
      }),
    }),
  );

  await page.getByPlaceholder("和搭子说句话…").fill("开始专注吧");
  await page.getByLabel("发送").click();
  const card = page.getByTestId("agent-action-card");
  await expect(card).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("sb_timer"))).toBeNull();

  await card.getByRole("button", { name: "确认" }).click();
  await expect(page).toHaveURL(/\/focus/);
  const timer = await page.evaluate(() => JSON.parse(localStorage.getItem("sb_timer") ?? "{}"));
  expect(timer.status).toBe("running");
  expect(timer.durationSeconds).toBe(30 * 60);
});
