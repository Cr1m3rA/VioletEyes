# VioletEyes-neo 开发计划（Development Plan）

> 版本：0.1.0-draft · 日期：2026-06-30
> 配套文档：[01-requirements.md](./01-requirements.md) · [02-specification.md](./02-specification.md)

---

## 0. 总览

### 0.1 时间表

| Phase | 名称 | 预估工时 | 关键交付 |
|---|---|---|---|
| **Phase 0** | 脚手架与预研 | 3–5 天 | monorepo 骨架 / 设计 token / CI / 部署陷阱排查 |
| **Phase 1** | 鉴权 + 项目 + 代码版本 | 8–12 天 | 登录/注册/项目 CRUD/zip&Git 接入/高危 bug 修复 |
| **Phase 2** | Skill 系统 | 8–12 天 | skill 上传/审核/启用/绑定/skill-schema |
| **Phase 3** | 扫描引擎 | 10–15 天 | 4 种模式/Agent Runtime/skill plan/队列/实时 |
| **Phase 4** | 报告 | 5–8 天 | Markdown/JSON/HTML/归档 |
| **Phase 5** | 视觉重构 + UI 完善 | 8–12 天 | 全站 VioletEyes 视觉 + 漏洞库 + Agent Trace |
| **Phase 6** | 收尾与上线 | 5–8 天 | 安全加固/可观测/Docker/文档/种子用户测试 |
| **合计** | | **47–72 天**（约 2–3 个月，单人或 2 人小团队） | |

### 0.2 里程碑

| Milestone | 触发条件 | 验收 |
|---|---|---|
| M0 | Phase 0 完成 | `pnpm dev` 起服务，`docker compose up` 起依赖 |
| M1 | Phase 1 完成 | 登录/项目/代码版本 端到端通过；6 个高危 bug 修复 |
| M2 | Phase 2 完成 | 上传一个 rce-scanner.zip，admin 审核通过，用户启用 |
| M3 | Phase 3 完成 | 4 种模式跑通 3 个样例仓库 |
| M4 | Phase 4 完成 | HTML 报告与 VioletEyes 模板字节级一致 |
| M5 | Phase 5 完成 | WCAG AA；所有页面 VioletEyes 视觉 |
| M6 | Phase 6 完成 | 内测就绪：CI 绿 / 文档齐 / seed 数据可演示 |

### 0.3 关键依赖

- Node 20 LTS、Python 3.11+、pnpm 10、Docker 24+
- LLM：Claude Opus 4.8（默认）+ OpenAI GPT（兜底）
- 第三方：`zod`、`@openai/agents`、`@anthropic-ai/sdk`、`jinja2`、`ast-grep`、`ripgrep`
- 不依赖 ShadowFox（黑盒联动 P2）

---

## Phase 0：脚手架与预研（3–5 天）

### 目标

把 骨架搬过来，但用 VioletEyes 视觉替换；准备好 monorepo + Docker + CI。

### 任务

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T0.1 | 复制 `D:\Code\` 到 VioletEyes-neo 分支 | — | 0.5 天 |
| T0.2 | docker-compose 移除子仓库强制挂载 + 启动时校验 secrets 熵（修复部署陷阱） | 安全规范 | 0.5 天 |
| T0.3 | Tailwind 3.4 → 4.x 升级（同步 VioletEyes 报告） | 规格 §2.2 | 0.5 天 |
| T0.4 | 添加 `packages/skill-schema`、`packages/report-theme` 两个 workspace | 规格 §11 | 1 天 |
| T0.5 | VioletEyes 报告 `templates/*.j2` + `inline/*` 迁入 `apps/api/templates/` | — | 0.5 天 |
| T0.6 | 设计 token（`packages/report-theme/tokens.css`）写入 Tailwind preset | 规格 §6.1 | 0.5 天 |
| T0.7 | GitHub Actions CI 改造（typecheck + test + lint + build + docker） | 安全规范 | 1 天 |
| T0.8 | README/CLAUDE.md 重写（明确"业务可行性测试"性质） | 需求 §0.3 | 0.5 天 |

### 交付

- `pnpm dev` 起 api + web
- `docker compose up` 起依赖
- CI 绿
- 设计 token 文档

### 验收

- 浏览器打开 `http://localhost:8090` 看到紫色 Logo
- 后端 `/api/health` 返回 `{status:'ok'}`
- 仓库根目录含 `docs/platform/{01,02,03}*.md`

---

## Phase 1：鉴权 + 项目 + 代码版本（8–12 天）

### 目标

把用户体系搭起来；项目/代码版本 CRUD 完整；**修复所有高危 bug**。

### 任务

#### 1.1 鉴权（3–4 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T1.1.1 | 启动校验：JWT_SECRET/APP_MASTER_KEY/SESSION_SECRET 长度 ≥ 32 + 熵足，否则 throw | 需求 NFR-SEC-06 | 0.5 天 |
| T1.1.2 | `auth.service.login` 改用 `or(eq(username), eq(email))` | 安全规范 | 0.5 天 |
| T1.1.3 | access 内存 + refresh HttpOnly + Secure + SameSite=Lax | 需求 NFR-SEC-05 | 1 天 |
| T1.1.4 | `updatePassword` 验旧密 + 强度校验 + 吊销**所有** refresh | 安全规范 | 0.5 天 |
| T1.1.5 | `JwtAuthGuard` 全局挂载（除 `@Public()`） | 需求 NFR-SEC-01 | 0.5 天 |
| T1.1.6 | `RolesGuard` 全局挂载 | 需求 NFR-SEC-02 | 0.5 天 |
| T1.1.7 | refresh_tokens 表加 `deviceLabel/userAgent/ip` | 规格 §3.1 | 0.5 天 |

#### 1.2 前端 auth（1–2 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T1.2.1 | LoginPage 改造：access 内存（Zustand）+ refresh HttpOnly 自动带 | 安全规范 | 1 天 |
| T1.2.2 | useAuth signOut 调 `/api/auth/logout` 吊销 refresh | 安全规范 | 0.5 天 |
| T1.2.3 | SettingsPage 改密后清 token + 跳登录 | 安全规范 | 0.5 天 |

#### 1.3 项目 + 代码版本（4–6 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T1.3.1 | `projects.service.create` 加 name 校验（trim 长度 ≤ 128） | 安全规范 | 0.5 天 |
| T1.3.2 | `code-versions.controller.upload` 加 `ProjectRoleGuard('editor')` | 安全规范 | 0.5 天 |
| T1.3.3 | zip 上传防护：解压比 ≤ 100 + 文件数 ≤ 100k + 单文件 ≤ 100MB + 无 `..` + 无 symlink | 需求 NFR-SEC-04 | 1 天 |
| T1.3.4 | `safeExtractZip` 改 try/finally 清 tempzip | 安全规范 | 0.5 天 |
| T1.3.5 | Git URL 校验：scheme 白名单 + host 限制 + 端口限制 | 安全规范 | 1 天 |
| T1.3.6 | `parseSourceRef` 用 URL parser（修 fragment 切错） | 安全规范 | 0.5 天 |
| T1.3.7 | `injectHttpsToken` 用 encodeURIComponent | 安全规范 | 0.5 天 |
| T1.3.8 | `randomHex` 改 `crypto.randomBytes` | 安全规范 | 0.5 天 |
| T1.3.9 | `code_versions` 表加 `sizeBytes/fileCount/locByLang/sha256` 落地 | 规格 §3.3 | 1 天 |

#### 1.4 测试（1 天）

- vitest 单测：auth/projects/code-versions 覆盖率 ≥ 80%

### 交付

- 用户能注册、登录、登出、改密
- 项目 CRUD + 成员管理
- zip / Git / GitHub 三种代码版本来源可用

### 验收

- 6 个高危 bug（auth 部分）修复完成
- 启动无密钥报错
- 单元测试通过

---

## Phase 2：Skill 系统（8–12 天）

### 目标

skill 上传、审核、启用、绑定完整闭环；schema 双实现（TS + Python）。

### 任务

#### 2.1 Skill Schema（2 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T2.1.1 | 编写 `packages/skill-schema/src/frontmatter.schema.json`（参考规格 §5.2） | 规格 §5.2 | 1 天 |
| T2.1.2 | TS 端 zod 派生（`packages/skill-schema/src/index.ts`） | — | 0.5 天 |
| T2.1.3 | Python 等价实现（`packages/skill-schema/src/py/frontmatter_schema.py`） | — | 0.5 天 |

#### 2.2 内置 Skill 迁入（2 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T2.2.1 | `skills/violeteyes-full/SKILL.md` —— 直接迁自 VioletEyes `../../SKILL.md` | — | 0.5 天 |
| T2.2.2 | `skills/framework-detect/` —— 包装 `scripts/framework_detect.py` | — | 0.5 天 |
| T2.2.3 | `skills/sink-detect/` —— 包装 `scripts/sink_detect.py` | — | 0.5 天 |
| T2.2.4 | `skills/route-mapper/`、`skills/auth-audit/`、`skills/supply-chain-cve/` | — | 0.5 天 |

#### 2.3 Skill 上传/审核（3–4 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T2.3.1 | `skill_bundles` + `skill_bundle_versions` 表 migration | 规格 §3.4 | 0.5 天 |
| T2.3.2 | `POST /api/skill-bundles/upload`：解压 + 校验 + 解析 SKILL.md + 入库 | 规格 §4.1 | 1.5 天 |
| T2.3.3 | 大小限制 ≤ 20MB + 文件数 ≤ 1000 + 解压比 ≤ 50 | 需求 NFR-SEC-10 | 0.5 天 |
| T2.3.4 | `SKILL.md` 大小 ≤ 256KB + schema 校验 | 需求 NFR-SEC-09 | 0.5 天 |
| T2.3.5 | admin 审核接口（`POST /api/admin/skills/:id/review`） | 规格 §4.1 | 0.5 天 |
| T2.3.6 | `SkillBundlesService.publish` / `setDefault` | — | 0.5 天 |
| T2.3.7 | **自动审核 — Lint 阶段**（必填字段、enum、长度上限、危险模式检测 `eval/exec/system/curl\|wget`） | 规格 §5.3.1 | 1 天 |
| T2.3.8 | **自动审核 — 沙箱执行**（隔离子进程 + filesystem/network/exec 限制 + 60s 超时 + 10k token 预算） | 规格 §5.3.1 | 1.5 天 |
| T2.3.9 | `SkillAutoReviewService` 串联 lint + sandbox，输出 `lintReport.json` + `sandboxReport.json` | 规格 §5.3.1 | 0.5 天 |

#### 2.4 项目 Skill 绑定（1–2 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T2.4.1 | `project_skill_bindings` 表 migration | 规格 §3.4 | 0.5 天 |
| T2.4.2 | `POST /api/projects/:id/skill-bindings` 启用 + 启停 toggle | 规格 §4.1 | 0.5 天 |
| T2.4.3 | 前端 Skill 管理页面（上传 + 列表 + 审核状态） | 规格 §6.4 | 1 天 |

### 交付

- 内置 6 个 skill 可用
- 用户能上传第三方 skill zip
- admin 可审核
- 用户可在项目里启停 skill

### 验收

- 上传一个 `rce-scanner.zip` 端到端跑通（上传 → admin 审核 → 用户启用）
- schema 校验失败时返回清晰错误

---

## Phase 3：扫描引擎（10–15 天）

### 目标

4 种扫描模式端到端跑通；Agent Runtime 独立进程；实时推送。

### 任务

#### 3.1 Agent Runtime（Python）（3–4 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T3.1.1 | `apps/agent/main.py` —— NDJSON stdin 循环 | 规格 §7.1 | 1 天 |
| T3.1.2 | `llm_client.py` —— 通过 stdin 协议向 api 中转请求 | 规格 §7.1 | 0.5 天 |
| T3.1.3 | `skill_loader.py` —— 解析 SkillPlan + 加载每个 skill | 规格 §7.3 | 1 天 |
| T3.1.4 | `tools/` —— filesystem/grep/ast/framework/cve 的 Python 包装 | 规格 §7.3 | 1 天 |
| T3.1.5 | sandbox 路径校验（`SandboxPath`） | 规格 §3.3 | 0.5 天 |

#### 3.2 Scan Planner（2 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T3.2.1 | `scan-planner.service.ts` —— Mode → SkillPlan 决策（QUICK/SMART/DEEP/CUSTOM 四种） | 规格 §5.4 | 1.5 天 |
| T3.2.2 | Smart 模式 LLM 决策记录（`smartDecision.selectedSkills[]` + `rejectedSkills[]` + `rationale`；LLM 仅从 `project.enabledSkills` 中挑选） | 规格 §5.4 | 0.5 天 |

#### 3.3 Scan Runner（3–4 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T3.3.1 | `scan-runner.service.ts` —— spawn agent subprocess | 规格 §7.2 | 1.5 天 |
| T3.3.2 | NDJSON 协议解析 + 心跳 + 取消信号 | 规格 §7.1 | 1 天 |
| T3.3.3 | `scanLogs` Map try/finally 清理（修内存泄漏） | 安全规范 | 0.5 天 |
| T3.3.4 | `coverage.util.ts` 拆 file-coverage vs route-coverage（修 filePath 当 route bug） | 安全规范 | 0.5 天 |
| T3.3.5 | 删 MVP fallback `mvpPct=100`（修覆盖率污染） | 安全规范 | 0.5 天 |

#### 3.4 Queue + 实时（2–3 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T3.4.1 | `scan-queue.service.ts` —— BullMQ + jobId 幂等 | 安全规范 | 1 天 |
| T3.4.2 | 并发控制（`SCAN_MAX_CONCURRENT` 默认 3） | 需求 §5.1 | 0.5 天 |
| T3.4.3 | WebSocket cookie auth + origin 白名单 + 订阅权限 | 需求 NFR-SEC-03 | 1 天 |
| T3.4.4 | 事件类型：`phase.start/end/log.line/finding.added/run.status` | 规格 §4.2 | 0.5 天 |

### 交付

- 4 种扫描模式在 3 个样例仓库（spring-boot/express/python-flask）端到端跑通
- 实时进度推送

### 验收

- 端到端测试：scan_run.status 从 queued → running → succeeded
- 杀掉 agent 子进程，scan_run.status 转 failed 且 scanLogs 清理
- WebSocket 客户端能实时看到 finding.added 事件

---

## Phase 4：报告（5–8 天）

### 目标

4 种格式报告 + VioletEyes 视觉一致。

### 任务

#### 4.1 Markdown + JSON（2 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T4.1.1 | `markdown.report.ts` —— 聚合所有 skill findings + 章节结构（含"执行概览 + 成本"章节） | 规格 §3.7 | 1.5 天 |
| T4.1.2 | `json.report.ts` —— 原始 findings + `cost` 字段透传 | 规格 §3.7 | 0.5 天 |

#### 4.2 HTML（2–3 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T4.2.1 | `html.report.ts` —— 调 agent 子进程的 `render_report.py`（迁自 VioletEyes） | 规格 §2.3 | 1.5 天 |
| T4.2.2 | 报告输入对齐（findings.json/assets.json/dependency_cve.json） | 规格 §5.3 | 1 天 |

#### 4.3 归档 + 下载（1–2 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T4.3.1 | `archive.report.ts` —— code version + findings + report + log zip | 规格 §3.7 | 1 天 |
| T4.3.2 | 下载鉴权（`JwtAuthGuard` + ProjectRoleGuard） | 安全规范 | 0.5 天 |
| T4.3.3 | `URL.createObjectURL` 必须 revoke | 安全规范 | 0.5 天 |

### 交付

- 4 种报告格式
- 下载链路鉴权

### 验收

- HTML 报告与 VioletEyes 模板字节级一致（diff `templates/base.html.j2` 渲染结果）
- 报告下载必须登录 + 项目成员

---

## Phase 5：视觉重构 + UI 完善（8–12 天）

### 目标

全站 VioletEyes 视觉；漏洞库；Agent Trace。

### 任务

#### 5.1 设计 Token 落地（1 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T5.1.1 | `packages/report-theme/tokens.css` 接入 apps/web `index.css` | 规格 §6.1 | 0.5 天 |
| T5.1.2 | Tailwind preset 接入 | 规格 §6.2 | 0.5 天 |

#### 5.2 核心组件（2–3 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T5.2.1 | `Logo`（渐变方块 + VE） | 规格 §6.3 | 0.5 天 |
| T5.2.2 | `SeverityBadge` + `SeverityBar` | 规格 §6.3 | 0.5 天 |
| T5.2.3 | `Cover`（紫光 + 网格 + 毛玻璃） | 规格 §6.3 | 0.5 天 |
| T5.2.4 | `Header`（sticky + backdrop-blur） | 规格 §6.3 | 0.5 天 |
| T5.2.5 | `Chart`（Chart.js 环形图 + 柱状图） | 规格 §6.3 | 0.5 天 |
| T5.2.6 | `Mermaid` + `CallChainTabs` | 规格 §6.3 | 0.5 天 |
| T5.2.7 | `FixDiff`（Before/After 双列） | 规格 §6.3 | 0.5 天 |

#### 5.3 页面视觉（3–5 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T5.3.1 | Login + Home 紫罗兰背景 | 规格 §6.4 | 0.5 天 |
| T5.3.2 | Projects 列表 / 详情 Tab | 规格 §6.4 | 1 天 |
| T5.3.3 | Scans 详情（阶段进度条 + 实时日志 + skill 卡片） | 规格 §6.4 | 1 天 |
| T5.3.4 | Report 页面（嵌入 HTML 或 iframe 隔离） | 规格 §6.4 | 1 天 |
| T5.3.5 | Skills 管理 + Vuln 库 + Agent Trace | 规格 §6.4 | 1.5 天 |

#### 5.4 漏洞库（1–2 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T5.4.1 | `vulnerabilities` + `finding_occurrences` 表 migration | 规格 §3.6 | 0.5 天 |
| T5.4.2 | `vuln-library.syncFromVulnerability` 修状态错位 | 安全规范 | 0.5 天 |
| T5.4.3 | `getTrend` 加 DB-side where + limit | 安全规范 | 0.5 天 |
| T5.4.4 | 趋势图（Chart.js 折线）+ 状态批量操作 | 规格 §6.4 | 0.5 天 |

### 交付

- 全站视觉统一为 VioletEyes 风格
- 漏洞库完整
- Agent Trace 可视化

### 验收

- WCAG AA 通过（自动化扫描）
- 与 VioletEyes 报告视觉对比一致
- 所有页面用 Logo + SeverityBadge 等统一组件

---

## Phase 6：收尾与上线（5–8 天）

### 目标

内测就绪：安全、可观测、可部署、有文档。

### 任务

#### 6.1 安全加固（2 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T6.1.1 | `timingSafeEqual` 用 `crypto.timingSafeEqual` | 安全规范 | 0.5 天 |
| T6.1.2 | Docker `||true` 移除 | 安全规范 | 0.5 天 |
| T6.1.3 | ConfigPage socks → socks5 统一 | 安全规范 | 0.5 天 |
| T6.1.4 | AppLayout admin 路由 `<RequireAdmin>` 包装 | 安全规范 | 0.5 天 |
| T6.1.5 | `LIKE` 通配符注入修复 | 安全规范 | 0.5 天 |

#### 6.2 可观测（1–2 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T6.2.1 | Prometheus 指标落地（规格 §9.1） | 规格 §9.1 | 1 天 |
| T6.2.2 | pino 结构化日志 | 规格 §9.2 | 0.5 天 |
| T6.2.3 | `/api/health` 完整实现 | 规格 §9.3 | 0.5 天 |

#### 6.3 Docker + 部署（1–2 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T6.3.1 | docker-compose.yml 三服务（api/web/redis） | 规格 §10.1 | 1 天 |
| T6.3.2 | nginx.conf SPA fallback + /api + /socket.io 反代 | 安全规范 | 0.5 天 |
| T6.3.3 | 默认 admin/admin123 强制改密流程 | 需求 §1.1 | 0.5 天 |

#### 6.4 文档（1 天）

| ID | 任务 | 来源 | 工时 |
|---|---|---|---|
| T6.4.1 | README + CLAUDE.md（业务可行性测试性质 + 启动指南） | 需求 §0.3 | 0.5 天 |
| T6.4.2 | skill 作者指南（如何写一个 SKILL.md） | 规格 §5.2 | 0.5 天 |

#### 6.5 内测种子数据（0.5 天）

- seed 三个项目（spring-boot / express / python-flask）
- seed 三个 skill 包
- 默认 admin + 两个 auditor 账号

### 交付

- Docker Compose 一键启动
- CI 全绿
- 内测用户可直接使用

### 验收

- `docker compose up` 后浏览器打开看到紫色首页
- 默认 admin/admin123 登录后强制改密
- 完整跑一次 Smart 模式扫描拿到 HTML 报告

---

## 风险与缓解

| 风险 | 触发 | 缓解 |
|---|---|---|
| Agent 子进程死锁 / 资源泄漏 | spawn 后 stdin 不关 | 设超时 + 心跳；finally 清理 |
| LLM Token 成本失控 | Deep 模式跑长 | 强制 max_tokens + max_iterations；超限自动 cancel |
| 第三方 skill prompt injection | 用户上传恶意 SKILL.md | NFR-SEC-09/10 + 签名校验 + admin 审核 |
| SQLite 写并发 | 多用户同时触发 scan | WAL + SCAN_MAX_CONCURRENT=3 + 队列 |
| OSV.dev 不可达 | 内网环境 | VioletEyes 离线缓存已落地 |
| Tailwind v4 升级兼容 | 已有组件失效 | Phase 0 早期 spike；保留 v3 fallback |

---

## 团队分工（2 人小团队参考）

| Phase | 人 A | 人 B |
|---|---|---|
| 0 | monorepo + Tailwind 4 + CI | Docker + 部署陷阱修复 |
| 1 | 后端 auth + 项目 + 代码版本 | 前端 auth + 路由 |
| 2 | skill schema + 内置 skill 迁入 | skill 上传审核 + 前端 Skill 中心 |
| 3 | Agent Runtime（Python） | Scan Planner + Runner + WebSocket |
| 4 | 报告（Markdown + JSON） | 报告（HTML + 归档） |
| 5 | 视觉组件 + Login/Home | 项目/扫描/漏洞库/Trace 页面 |
| 6 | 安全 + 可观测 | Docker + 文档 + 种子数据 |

---

## 文档索引

- 需求 → [01-requirements.md](./01-requirements.md)
- 规格 → [02-specification.md](./02-specification.md)
-  bug 探索 → §6 / 安全规范
- VioletEyes 原版 → `../../SKILL.md`