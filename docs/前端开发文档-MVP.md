# 前端开发文档（MVP 阶段）｜AI 学习搭子 · 自习室

> ⚠️ **历史版本**：本文记录已归档的后端内嵌 H5，不代表当前正式前端。当前正式前端位于 `frontend/`。
>
> 配套：《前端技术适配声明》、PRD《study-buddy.md》、后端 routes.py / schemas.py
> 状态：✅ MVP 前端已落地，本文档记录当前实现
> 前端形态：单文件 H5（`backend/app/static/index.html`，原生 HTML/CSS/JS）

---

## 1. 本阶段目标

用户打开链接进入「自习室」，即可：看到写实真人形象的搭子陪伴、文字/语音聊天、番茄钟专注、在「我的」页回顾学习记录。

## 2. 范围

### 本阶段包含

- **页面**：陪伴页、专注页、我的页（单文件三 Tab，底部导航切换）
- **组件**：视频窗口、搭子形象（男女切换）、字幕打字机、聊天历史、输入栏（文字 + 麦克风）、番茄钟、打卡日历、统计卡片、语音开关
- **接口**：chat / encourage / tts / stats / stats/complete / history（goal 保留未接）
- **状态**：对话 busy、番茄钟四态、语音开关、主动搭话
- **产物**：语音（MP3）、形象图（静态 JPEG）

### 本阶段不包含

- Next.js / TypeScript 工程化
- 账号系统、云同步、多人
- 学科答疑
- 成就徽章、每日目标、学习周报（候选功能）

## 3. 用户流程

1. 打开页面 → 进入「陪伴」页，搭子语音打招呼
2. 切换男女形象、开关语音
3. 文字输入或按住 🎤 说话 → 搭子文字 + 语音回复
4. 切到「专注」页 → 开始番茄钟 → 过半鼓励 → 完成庆祝 + 计数 → 自动切休息
5. 切到「我的」页 → 看累计统计 + 打卡日历

## 4. 页面状态矩阵

| 页面/模块 | 初始 | 加载 | 空 | 运行 | 成功 | 失败 | 恢复 |
|---|---|---|---|---|---|---|---|
| 陪伴页聊天 | 显示搭子 | 发送时按钮禁用 | — | 打字机 + 光晕 | 正常回复 | 兜底文案「信号不好」 | 刷新后历史清空（会话态） |
| 语音输出 | 静默 | TTS 请求中 | — | 播放中光晕 | 播放完关闭 | 静默降级纯字幕 | — |
| 语音输入 | 麦克风可用 | 识别中红点 | — | 按住监听 | 识别文本发送 | 权限拒绝提示打字 | 自动重启识别 |
| 番茄钟 | 25:00 | — | — | 倒计时 | 完成庆祝 | — | localStorage 恢复计时 |
| 我的页统计 | 显示 0 | 拉取中 | 空数据显示 0 | — | 展示累计 | 静默显示 0 | 每次进页重拉 |

## 5. 接口契约

统一前缀 `/api/v1`，错误结构 `{"error": {"code", "message"}}`。

| 接口 | 请求 | 成功返回 |
|---|---|---|
| POST `/chat` | `{message: 1-200, goal?: ≤60}` | `{reply, source: "llm"\|"local"}` |
| POST `/encourage` | `{scene: greet\|start\|encourage\|celebrate\|break\|breakOver\|tired\|idle}` | `{reply}` |
| POST `/tts` | `{text: 1-200, gender?: male\|female}` | MP3 流（失败 204） |
| GET `/stats` | — | `{date, tomato, minutes, streak, weekDays[]}` |
| POST `/stats/complete` | `{minutes: 1-600}` | 更新后 stats |
| GET `/history` | — | `{days{}, totalTomato, totalMinutes}` |

## 6. 实现方案

- **路由**：单文件三 `.page` 区块 + `switchTab()` 显隐切换（非 URL 路由）
- **组件结构**：DOM 节点 + `$()` 查询，无组件化
- **状态来源**：后端 stats/history 为事实来源；前端 `localStorage` 存 `sb_timer`（计时）、`sb_buddy`（形象）、`sb_voice`（语音开关）
- **说话链路**：`speak()` = 字幕打字机（`typeTo`）+ `playVoice()`（fetch `/tts` → blob → Audio 播放）；`stopSpeech()` 打断；`speechGen` 代际防旧覆盖
- **语音输入**：Web Speech API（`SpeechRecognition`），Pointer Events 按住说话，`continuous=true` 持续监听、意外结束自动重启
- **响应式**：`max-width: 480px` 居中，移动端优先
- **安全与隐私**：模型 Key 仅在后端 `.env`，前端零密钥；无用户隐私上传

## 7. 验收标准

- **自动检查**：后端 `pytest` 40 passed；前端 `node --check` 语法通过
- **真实浏览器**：桌面 Chrome 走通「聊天 → 语音 → 番茄 → 我的」全流程
- **真机**：语音输入需真机（含 iPhone）验证，非 HTTPS 环境预期受限
- **回归点**：刷新后计时/形象/语音开关状态保持；番茄完成计数正确；日历当天高亮

## 8. 风险与回退

| 风险 | 降级/回退 |
|---|---|
| iOS / 非 HTTPS 语音输入不可用 | 自动退回文字输入 |
| edge-tts 联网失败 | 降级纯字幕 |
| 单文件可维护性下降 | 功能增长时迁移 Next.js + TS |
| 免费模型限流 | 后端内置引擎兜底 |

## 9. 交付结果

- **文件**：`backend/app/static/index.html`、`assets/buddy-male.jpg`、`assets/buddy-female.jpg`
- **检查结果**：后端 pytest 40 passed；前端 node --check 通过；浏览器人工验收通过
- **未完成项**：正式前端工程化（Next.js/TS）、前端自动化测试、部署
- **已知问题**：手机局域网 HTTP 下语音输入受限（需部署 HTTPS 解决）
