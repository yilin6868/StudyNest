import { test, expect, type Page } from "@playwright/test";
import { registerAccount } from "./helpers";

async function login(page: Page) {
  await registerAccount(page);
}

test("关闭语音后陪伴页和专注页都不请求 TTS", async ({ page }) => {
  let ttsRequests = 0;
  await page.route("**/api/v1/tts", (route) => {
    ttsRequests += 1;
    return route.fulfill({ status: 204 });
  });

  await login(page);
  const voiceSwitch = page.getByRole("switch");
  await expect(voiceSwitch).toHaveAttribute("aria-checked", "false");

  await page.getByText("🥱 我有点累").click();
  await expect(page.locator(".self-start").first()).toBeVisible();
  expect(ttsRequests).toBe(0);

  await page.getByRole("link", { name: "专注" }).click();
  await page.getByRole("button", { name: "开始专注" }).click();
  await expect(page.getByRole("button", { name: "暂停" })).toBeVisible();
  await page.waitForTimeout(300);
  expect(ttsRequests).toBe(0);
});

test("语音开关跨页面保持一致", async ({ page }) => {
  let ttsRequests = 0;
  await page.route("**/api/v1/tts", (route) => {
    ttsRequests += 1;
    return route.fulfill({ status: 204 });
  });

  await login(page);
  const voiceSwitch = page.getByRole("switch");
  await voiceSwitch.click();
  await expect(voiceSwitch).toHaveAttribute("aria-checked", "true");
  await page.getByText("🥱 我有点累").click();
  await expect.poll(() => ttsRequests).toBeGreaterThan(0);

  await voiceSwitch.click();
  await expect(voiceSwitch).toHaveAttribute("aria-checked", "false");
  const beforeFocus = ttsRequests;
  await page.getByRole("link", { name: "专注" }).click();
  await page.getByRole("button", { name: "开始专注" }).click();
  await page.waitForTimeout(300);
  expect(ttsRequests).toBe(beforeFocus);
});

test("没有麦克风时仍可文字聊天且没有 hydration 错误", async ({ page }) => {
  const hydrationErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error" && message.text().toLowerCase().includes("hydration")) {
      hydrationErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    if (error.message.toLowerCase().includes("hydration")) hydrationErrors.push(error.message);
  });
  await page.addInitScript(() => {
    Object.defineProperty(window, "SpeechRecognition", { value: undefined, configurable: true });
    Object.defineProperty(window, "webkitSpeechRecognition", {
      value: undefined,
      configurable: true,
    });
  });
  await page.route("**/api/v1/tts", (route) => route.fulfill({ status: 204 }));

  await login(page);
  await expect(page.getByText("当前浏览器不支持语音输入，请使用文字输入。")).toBeVisible();
  await page.getByPlaceholder("和搭子说句话…").fill("文字聊天正常吗");
  await page.getByLabel("发送").click();
  await expect(page.locator(".self-start").first()).toBeVisible();
  expect(hydrationErrors).toEqual([]);
});
