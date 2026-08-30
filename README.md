# AI 学习搭子 · 自习室

一个「打开即进入自习室」的 H5：写实真人形象的 AI 搭子「小悟」🦉 陪你视频学习、开口聊天、番茄专注、记录成长。

当前已完成 **第 1、2 阶段**：核心能力 API 化（FastAPI）+ 真人感陪伴（写实形象 / 双向语音 / 番茄钟 / 我的板块）。

## 目录结构

```
AI学习搭子/
├── backend/                 # FastAPI 后端 + 前端 H5
│   ├── app/
│   │   ├── api/routes.py    # /api/v1/* 路由
│   │   ├── core/config.py   # 读 .env 配置
│   │   ├── schemas/         # Pydantic 请求/响应
│   │   ├── services/        # 对话、内置引擎、统计、历史、语音合成、存储
│   │   ├── static/          # 前端 H5（薄客户端 + 搭子形象图）
│   │   └── main.py          # FastAPI 入口
│   ├── tests/               # pytest 自动化测试
│   ├── data/                # 运行时数据（stats/goal/history.json，已 gitignore）
│   ├── .env.example         # 配置模板（复制为 .env 后填 Key）
│   └── requirements.txt
├── docs/                    # PRD、手册、技术适配声明、阶段文档
├── study-buddy.md           # PRD 推导方案
└── AI产品Vibe Coding通用技术栈手册.md
```

## 快速开始

### 1. 准备环境

```bash
cd backend
python3 -m venv .venv                              # 首次
.venv/bin/pip install -r requirements.txt          # 首次
```

### 2. 配置（可选，不配也能用内置引擎）

```bash
cp .env.example .env
# 编辑 .env，设置登录邀请码与签名密钥；模型 Key 可选
```

默认模型：GLM-4-Flash（`https://open.bigmodel.cn/api/paas/v4`，model `glm-4-flash`，免费）。
换模型只需改 `.env` 的 `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`，不改代码。

### 3. 启动

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# 浏览器/手机打开 http://localhost:8000
```

### 4. 运行测试

```bash
cd backend
.venv/bin/python -m pytest -q
```

## API（统一前缀 /api/v1）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/chat` | 搭子对话（有 Key 走默认模型，失败/无 Key 回退内置引擎） |
| POST | `/api/v1/encourage` | 场景话术（greet/start/encourage/celebrate/break/breakOver/tired/idle） |
| POST | `/api/v1/tts` | 文字转语音（按男女形象选音色，返回 MP3） |
| GET | `/api/v1/stats` | 统计（番茄数/连续天数/本周专注天数） |
| POST | `/api/v1/stats/complete` | 完成一个番茄钟（同时记录每日历史） |
| GET | `/api/v1/history` | 每日历史记录 + 累计番茄/时长 |
| GET | `/api/v1/goal` | 读今日目标 |
| PUT | `/api/v1/goal` | 保存今日目标 |

错误统一返回：`{"error": {"code": "...", "message": "..."}}`。

## 产品功能

- 👥 **写实真人搭子**：都市现代风男生/女生形象可切换，视频陪伴画面
- 💬 **陪伴**：文字聊天 + 搭子语音回复（TTS）+ 你按住说话（ASR）+ 长时间无交互主动搭话 + 说话可打断
- 🎚️ **语音开关**：关闭则纯文字聊天（布局不变，仅静音）
- 🍅 **专注**：番茄钟（25 分钟专注 / 5 分钟休息），过半自动打气、完成庆祝 + 计数，刷新恢复计时
- 👤 **我的**：统计总览（累计番茄/累计时长/连续天数/本周专注）+ 打卡日历（月视图）+ 每日历史
- 🧠 **真人感人设**：像真人朋友，聊日常/压力/情绪，**不聊专业知识**（问学科题目礼貌回避）

## 数据

- 后端：`backend/data/stats.json`（今日快照）、`history.json`（每日历史）、`goal.json`（JSON + schemaVersion + 原子写入）
- 前端 `localStorage`：`sb_timer`（计时进度）、`sb_buddy`（形象选择）、`sb_voice`（语音开关）

## 线上访问（已上线）

- **前端入口**：https://sgej7obvkf9v1ituvo05m.apigateway-cn-beijing.volceapi.com/
- **后端 API**：https://sjaqvvimvqsd7r6nucape.apigateway-cn-beijing.volceapi.com/
- **访问方式**：邀请码由部署者通过后端环境变量 `INVITE_CODES` 配置和分发
- 登录后进入自习室；数据按邀请码隔离，每人独立

## 阶段状态

- ✅ 第 1 阶段（后端开发）：核心能力 API 化 + 双层验收通过（pytest + GLM-4-Flash 真实冒烟）
- ✅ 第 2 阶段（真人感陪伴）：写实形象 + 双向语音 + 番茄钟 + 我的板块
- ✅ 正式前端（Next.js + TS）：三页 + 登录 + Playwright E2E
- ✅ 部署公网（火山引擎 veFaaS）：前后端分别部署 + 邀请码登录 + 数据隔离
- ⏸ 埋点（后续）
- 💡 后续候选功能：成就徽章、每日目标、学习周报（搭子播报）

## 开源许可

本项目采用 [MIT License](LICENSE) 开源。
