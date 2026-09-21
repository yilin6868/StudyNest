import { defineConfig } from "@playwright/test";

const backendPython = process.env.STUDY_BUDDY_PYTHON ?? ".venv/bin/python";
const backendPort = process.env.E2E_BACKEND_PORT ?? "8000";
const frontendPort = process.env.E2E_FRONTEND_PORT ?? "3000";

if (!/^\d+$/.test(backendPort) || !/^\d+$/.test(frontendPort)) {
  throw new Error("E2E 端口必须是数字");
}

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  // 这些用例共用同一个测试账号和临时数据目录，串行执行可避免互相抢占登录/统计状态。
  workers: 1,
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    channel: "chrome", // macOS 13 不支持 Playwright 内置 chromium，复用系统 Chrome
    viewport: { width: 390, height: 844 }, // 移动端优先尺寸
  },
  webServer: [
    {
      command:
        `cd ../backend && ${JSON.stringify(backendPython)} -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      url: `http://127.0.0.1:${backendPort}/health`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: `HOSTNAME=127.0.0.1 PORT=${frontendPort} node .next/standalone/server.js`,
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
