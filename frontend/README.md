# AI 学习搭子正式前端

这里是项目唯一的正式用户前端，技术栈为 Next.js 16、React 19 和 TypeScript。

## 启动

先按项目根目录 README 启动 FastAPI 后端，再执行：

```bash
npm ci
BACKEND_URL=http://localhost:8000 npm run dev
```

浏览器打开 `http://localhost:3000`。`BACKEND_URL` 只供 Next.js 服务端配置 API 转发使用，浏览器仍然请求同源的 `/api/v1/*`。

## 常用命令

```bash
npm run dev             # 本地开发
npm run lint            # 代码检查
npm run build           # 使用 webpack 生成生产构建
npm run build:turbopack # 仅用于排查 Turbopack 构建状态
npm run test:e2e        # 使用隔离测试环境运行浏览器测试
```

端到端测试必须通过 `npm run test:e2e` 或项目根目录的 `scripts/run-e2e.sh` 启动。不要直接给测试填入真实邀请码，也不要连接生产后端。

## 页面

| 路径 | 用途 |
|---|---|
| `/login` | 账号登录，或使用邀请码注册新账号 |
| `/` | 学习搭子聊天和形象设置 |
| `/focus` | 番茄专注 |
| `/profile` | 学习统计和历史 |

## 目录

- `src/app/`：页面和全局样式。
- `src/components/`：公共组件。
- `src/lib/api/`：后端请求封装和类型。
- `src/lib/auth.ts`：当前登录凭证的本地管理。
- `public/assets/`：正式前端使用的搭子图片。
- `e2e/`：Playwright 浏览器测试。

早期单文件网页和后端内嵌 H5 已放入项目根目录的 `archive/`，禁止从归档目录部署。
