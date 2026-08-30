import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:3000",
    channel: "chrome", // macOS 13 不支持 Playwright 内置 chromium，复用系统 Chrome
    viewport: { width: 390, height: 844 }, // 移动端优先尺寸
  },
  webServer: [
    {
      command:
        "cd ../backend && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000",
      url: "http://localhost:8000/api/v1/stats",
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
