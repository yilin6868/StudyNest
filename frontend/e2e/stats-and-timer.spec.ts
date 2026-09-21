import { randomUUID } from "node:crypto";
import { test, expect, type Page } from "@playwright/test";
import { registerAccount } from "./helpers";

async function login(page: Page) {
  await registerAccount(page);
}

async function getStats(page: Page) {
  return page.evaluate(async () => {
    const token = localStorage.getItem("sb_token");
    const response = await fetch("/api/v1/stats", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.json() as Promise<{ tomato: number; minutes: number }>;
  });
}

function expiredTimer(sessionId: string) {
  return {
    schemaVersion: 2,
    sessionId,
    mode: "focus",
    status: "running",
    startedAt: Date.now() - 26 * 60 * 1000,
    endAt: Date.now() - 60 * 1000,
    remainingSeconds: 1,
    halfDone: true,
  };
}

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/tts", (route) => route.fulfill({ status: 204 }));
  await login(page);
});

test("运行中的计时刷新后按结束时间恢复", async ({ page }) => {
  const sessionId = randomUUID();
  await page.evaluate(
    ({ id }) => {
      localStorage.setItem(
        "sb_timer",
        JSON.stringify({
          schemaVersion: 2,
          sessionId: id,
          mode: "focus",
          status: "running",
          startedAt: Date.now() - 10_000,
          endAt: Date.now() + 90_000,
          remainingSeconds: 90,
          halfDone: false,
        }),
      );
    },
    { id: sessionId },
  );

  await page.goto("/focus");
  await expect(page.getByText(/01:(2[7-9]|30)/)).toBeVisible();
  await page.reload();
  await expect(page.getByText(/01:(2[5-9]|30)/)).toBeVisible();
});

test("页面关闭期间结束后补结算且重复刷新不重复记账", async ({ page }) => {
  const sessionId = randomUUID();
  const before = await getStats(page);
  await page.evaluate((timer) => localStorage.setItem("sb_timer", JSON.stringify(timer)), expiredTimer(sessionId));

  await page.goto("/focus");
  await expect(page.getByText("本次专注已保存。")).toBeVisible();
  const afterFirst = await getStats(page);
  expect(afterFirst.tomato).toBe(before.tomato + 1);
  expect(afterFirst.minutes).toBe(before.minutes + 25);

  await page.evaluate((timer) => localStorage.setItem("sb_timer", JSON.stringify(timer)), expiredTimer(sessionId));
  await page.reload();
  await expect(page.getByText("本次专注已保存。")).toBeVisible();
  expect(await getStats(page)).toEqual(afterFirst);
});

test("保存失败不制造假数据并可用原 sessionId 重试", async ({ page }) => {
  const sessionId = randomUUID();
  const before = await getStats(page);
  let failNextCompletion = true;
  await page.route("**/api/v1/stats/complete", async (route) => {
    if (failNextCompletion) {
      failNextCompletion = false;
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "TEST_FAILURE", message: "测试保存失败" } }),
      });
      return;
    }
    await route.continue();
  });
  await page.evaluate((timer) => localStorage.setItem("sb_timer", JSON.stringify(timer)), expiredTimer(sessionId));

  await page.goto("/focus");
  await expect(page.getByText("本次专注保存失败，请重新保存。")).toBeVisible();
  expect(await getStats(page)).toEqual(before);

  await page.getByRole("button", { name: "重新保存" }).click();
  await expect(page.getByText("本次专注已保存。")).toBeVisible();
  const after = await getStats(page);
  expect(after.tomato).toBe(before.tomato + 1);
  expect(after.minutes).toBe(before.minutes + 25);
});
