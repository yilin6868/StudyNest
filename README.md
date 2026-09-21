# StudyNest

StudyNest 是一款移动端优先的学习陪伴产品。当前正式产品由一个 Next.js 前端和一个 FastAPI 后端组成：前端负责页面和交互，后端负责登录、聊天、鼓励话术、语音、专注数据与历史记录。

在线演示：[打开 StudyNest](https://s3rqv8m7s6ccmbo164u7i.apigateway-cn-beijing.volceapi.com/login)。体验需要邀请码；演示环境不持久保存账号、会话和学习记录。

> 当前开发阶段：P1-C「记忆、安全与可观测性」工程开发和隔离自动验收已完成。项目已具备最小 Agent Harness 的工程组成，但人工安全复核、真实模型冒烟和 PostgreSQL 实库验收仍是发布阻塞项。

## 哪些目录是正式版本

| 目录 | 用途 | 是否正式运行 |
|---|---|---|
| `frontend/` | Next.js 正式前端 | 是 |
| `backend/` | FastAPI 正式后端 API | 是 |
| `docs/` | 产品与历史阶段文档 | 文档 |
| `开发技术手册/` | 当前开发规则、阶段手册和验收记录 | 文档 |
| `archive/` | 早期原型、旧 H5、历史 PRD | 否，禁止部署 |

后端不再提供产品网页。访问产品时请打开前端地址，后端的运行状态通过 `GET /health` 检查。

## 本地启动

### 1. 启动后端

需要 Python 3.11 或更高版本。

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m app.cli.manage_invites create --max-uses 2
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`.env.example` 中只有本地示例值。第一次启动先执行数据库升级，再用管理命令创建邀请码。命令只在创建时显示一次邀请码，请自行安全保存。生产环境必须使用 PostgreSQL，并自行设置安全的密钥，不能直接使用示例值。

后端启动后可访问：

- 健康检查：`http://localhost:8000/health`
- 就绪检查：`http://localhost:8000/ready`
- API 文档：`http://localhost:8000/docs`

### 2. 启动前端

另开一个终端，需要 Node.js 20 或更高版本。

```bash
cd frontend
npm ci
BACKEND_URL=http://localhost:8000 npm run dev
```

浏览器打开 `http://localhost:3000`。可以输入邀请码直接体验，也可以使用邀请码注册账号，再用用户名和密码登录。

## 运行检查

安装好前后端依赖后，在项目根目录运行：

```bash
./scripts/verify.sh
```

脚本会依次执行后端测试、前端代码检查、webpack 生产构建和浏览器端到端测试。端到端测试使用临时数据目录、测试邀请码和本地回复，不会读取真实用户数据，也不会调用真实模型。

也可以单独运行：

```bash
(cd backend && .venv/bin/python -m pytest -q)
(cd frontend && npm run lint)
(cd frontend && npm run build)
(cd frontend && npm run test:e2e)
```

## 更新已有 veFaaS 部署

### 无持久化演示版

个人账号仅需外网体验时，可将后端设置为 `STUDYNEST_APP_ENV=demo`、`DATA_DIR=/tmp/data`，并配置独立的强随机 `AUTH_SECRET`、`INVITE_CODE_PEPPER`、`LOG_PSEUDONYM_SECRET` 和 `DEMO_INVITE_CODE`。演示模式会在每个新实例启动时自动执行数据库迁移，并创建不限次数的体验邀请码。此模式只适合体验：函数实例回收、扩缩容或重新部署后，账号、会话和学习记录可能消失；不同实例的数据也可能不一致。正式上线仍须使用下面的 PostgreSQL 流程。

前端和后端是两个已分别绑定的 veFaaS 应用。后续迭代应部署已有的 `studynest-backend`、`studynest-frontend`，不要再用 `--newApp` 创建重复应用。

发布前先建立可回滚的 Git 提交，然后运行：

```bash
STUDY_BUDDY_PYTHON=/path/to/python ./scripts/verify-release.sh
```

生产后端必须使用 `STUDYNEST_APP_ENV=production` 和外部 PostgreSQL（本地可用 `APP_ENV=production`）。不允许把 veFaaS `/tmp` 中的 SQLite 当作生产数据库。包含 Alembic 迁移的更新按以下顺序执行：

1. 备份生产 PostgreSQL，并确认备份可恢复。
2. 在单一受控任务中对生产连接执行 `python -m alembic upgrade head`。
3. 执行 `python -m app.cli.release_check`，确认配置、PostgreSQL 和迁移版本均就绪。
4. 先覆盖部署后端，验证 `/health` 和 `/ready` 均返回 200。
5. 再使用真实后端公网地址执行 `npm run build:standalone` 并覆盖部署前端。

`build:standalone` 会把 `.next/static` 和 `public` 一起放入独立部署产物，避免上线后头像和样式丢失。本地验证不会自动访问或修改线上环境。

## 主要接口

除健康检查和登录外，业务接口都需要登录凭证。

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health` | 后端健康检查 |
| GET | `/ready` | 检查数据库和数据库版本是否就绪 |
| POST | `/api/v1/auth/register` | 使用邀请码、用户名和密码注册 |
| POST | `/api/v1/auth/login` | 使用用户名和密码登录 |
| GET | `/api/v1/auth/session` | 向后端确认当前登录凭证有效 |
| POST | `/api/v1/auth/logout` | 撤销当前登录凭证 |
| POST | `/api/v1/chat` | 版本 `1.2` 的有限 Agent 对话 |
| POST、GET | `/api/v1/chat/sessions` | 新建或查看本人最近会话 |
| GET | `/api/v1/chat/sessions/{sessionId}/messages` | 恢复本人会话的最近消息 |
| DELETE | `/api/v1/chat/sessions/{sessionId}` | 删除本人会话及消息 |
| GET | `/api/v1/memories` | 查看本人的三类学习记忆 |
| PUT、DELETE | `/api/v1/memories/{category}` | 修改或删除本人的指定记忆 |
| POST | `/api/v1/agent/actions/resolve` | 确认或取消一次性开始/暂停动作 |
| POST | `/api/v1/agent/focus-summary` | 根据本人真实完成记录生成总结 |
| POST | `/api/v1/encourage` | 获取场景鼓励话术 |
| POST | `/api/v1/tts` | 文字转语音 |
| GET | `/api/v1/stats` | 获取学习统计 |
| POST | `/api/v1/stats/complete` | 记录一次专注完成；必须提交唯一 `sessionId` |
| GET | `/api/v1/history` | 获取学习历史 |
| GET、PUT | `/api/v1/goal` | 读取或保存今日目标 |

完成一轮专注的请求示例：

```json
{
  "sessionId": "0f6f75ce-7d67-46e4-97b4-6bdf963f8495",
  "minutes": 25
}
```

同一个用户重复提交同一个 `sessionId` 时，数据库只记账一次。统计以数据库中的每日记录为事实来源，并按用户时区（默认 `Asia/Shanghai`）计算今天、本周和连续学习天数。旧 JSON 文件只供迁移和核对，不再承接正式写入。

## 最小 Agent Harness 现状

正式聊天接口已经接入有限 Agent Runtime。它最多进行固定次数的模型判断和工具调用，写工具会核对用户原话与具体参数；Agent 只能看到白名单学习工具，不能看到或调用可信结算工具。

开始或暂停专注只会先显示确认卡片。后端签发短期、一次性凭证，用户确认后前端才执行白名单动作。聊天首页和专注页现在共用数据库里的今日目标；完成总结只读取本人已经结算的真实记录。无模型 Key 或模型异常时，普通聊天和完成总结会使用本地安全回复。

聊天现在会按用户保存有界会话，支持刷新恢复和新对话隔离。长期记忆只允许学习习惯、学习偏好和陪伴风格三类，由用户查看、修改和删除。明显危机表达在模型前被程序拦截，不调用模型和学习工具，且不保存危机原文。每次 Agent 请求同时留下不含对话正文的脱敏轨迹。

因此当前可称为“具备最小 Agent Harness 工程组成”，但不能称为“已可无条件正式上线”。

内部脱敏轨迹查询示例：

```bash
cd backend
.venv/bin/python -m app.cli.agent_trace --request-id req_xxx
.venv/bin/python -m app.cli.agent_metrics --hours 24
```

旧 JSON 迁移命令默认只演练、不写数据库：

```bash
cd backend
.venv/bin/python -m app.cli.migrate_json dry-run --data-dir ./data
# 只有完成备份并明确批准后，才可执行：
# .venv/bin/python -m app.cli.migrate_json import --data-dir ./data --backup-confirmed
```

## 配置说明

| 配置 | 说明 |
|---|---|
| `APP_ENV` / `STUDYNEST_APP_ENV` | `development`、`test`、`demo` 或 `production`；veFaaS 使用后者 |
| `APP_TIMEZONE` | 应用时区，默认 `Asia/Shanghai` |
| `DATABASE_URL` | 数据库连接地址；本地可用 SQLite，生产必须用 PostgreSQL |
| `INVITE_CODE_PEPPER` | 邀请码摘要密钥；生产环境必须替换 |
| `AUTH_SECRET` | 只用于短期旧账号认领；生产环境仍必须替换默认值 |
| `AUTH_TOKEN_TTL_SECONDS` | 登录有效期，默认 30 天 |
| `ALLOW_LEGACY_TOKENS` | 旧账号认领开关，默认关闭 |
| `DATA_DIR` | 只用于读取待迁移的旧 JSON |
| `LLM_API_KEY` | 可选；为空时使用本地回复 |
| `LLM_BASE_URL`、`LLM_MODEL` | 模型接口地址和模型名 |
| `AGENT_MAX_MODEL_TURNS` | 单次对话最多模型判断次数，默认 4 |
| `AGENT_MAX_TOOL_CALLS` | 单次对话最多工具调用数，默认 3 |
| `AGENT_MODEL_TIMEOUT_SECONDS` | 单次模型调用超时，默认 10 秒 |
| `AGENT_TOTAL_TIMEOUT_SECONDS` | 单次 Agent 对话总超时，默认 25 秒 |
| `AGENT_ACTION_TTL_SECONDS` | 开始/暂停确认凭证有效期，默认 300 秒 |
| `CHAT_RECENT_MESSAGE_LIMIT`、`CHAT_PAGE_MESSAGE_LIMIT` | 模型上下文和页面恢复的消息上限 |
| `CHAT_SUMMARY_*`、`AGENT_CONTEXT_MAX_BYTES` | 会话摘要触发条件和总上下文上限 |
| `AGENT_TRACE_MAX_EVENTS` | 单次请求的脱敏事件上限，默认 50 |
| `LOG_PSEUDONYM_SECRET` | 日志用户匿名密钥；生产环境必须单独设置 |

真实 `.env`、运行数据和部署配置均不应提交到 Git。

## 开发规则

- 项目级技术路线以 `开发技术手册/后端开发技术适配声明.md` 为准。
- 每个阶段先确认开发技术手册，再开发，再填写验收记录。
- `archive/` 只用于回看产品演进，不作为修复或部署入口。
- P1-C 最小 Agent Harness 工程组成已建立；人工安全复核、真实模型、PostgreSQL 和发布检查通过前不得宣称可正式上线。
