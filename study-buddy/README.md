# AI 学习搭子 · 自习室（历史版本 · 单文件 H5）

> ⚠️ **本目录是第 0 阶段的单文件 H5 原型，已归档。**
> 第 1 阶段已迁移为 FastAPI 后端 + 薄客户端：前端在 `backend/app/static/index.html`，核心能力 API 化。
> 启动方式与最新说明见根目录 `README.md`（`cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000`）。

一个「打开即进入自习室」的 H5：AI 搭子「小悟」🦉 陪你专注、鼓励你、为你打卡庆祝。

## 打开方式（任选其一，仅针对本旧版单文件）

1. **直接双击**：打开 `index.html`（浏览器即可，无需联网、无需部署）
2. **本地起服务**：
   ```bash
   cd study-buddy
   python3 -m http.server 8000
   # 然后浏览器打开 http://localhost:8000
   ```
3. **手机访问**：把 `index.html` 上传到任意静态托管（GitHub Pages / 妙搭 / veFaaS 等），得到分享链接后手机打开。

## 功能（旧版）

- 🦉 **AI 搭子「小悟」**：打字机式说话，点击它可求鼓励
- 🍅 **番茄钟**：25 分钟专注 / 5 分钟休息，到一半会自动打气，完成自动庆祝并计数
- 🎯 **今日目标**：写下目标，搭子会记住并回应
- 💬 **聊天**：快捷按钮 + 自由输入
- 🔥 **连续打卡**：番茄数、连续天数本地记录
- ⚙️ **真·AI 模式**：旧版在前端设置里填 OpenAI 兼容接口 + Key；新版已把 Key 移到后端 `.env`

## 文件说明

| 文件 | 说明 |
|---|---|
| `index.html` | 旧版自习室 H5（单文件，自包含，无依赖） |
| `../backend/app/static/index.html` | 新版前端（薄客户端，调后端 `/api/v1/*`） |
| `../study-buddy.md` | PRD 推导方案 |
