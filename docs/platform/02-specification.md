# VioletEyes-neo 技术规格（Specification）

> 版本：0.1.0-draft · 日期：2026-06-30
> 配套文档：[01-requirements.md](./01-requirements.md) · [03-development-plan.md](./03-development-plan.md)

---

## 0. 范围

本文档描述 VioletEyes-neo 的**系统架构、数据模型、模块设计、API 表面、扫描模式语义、技能系统、视觉设计、部署形态**。不重复需求文档的功能/非功能条目，所有需求追溯请回到 `01-requirements.md`。

---

## 1. 系统架构总览

### 1.1 仓库结构

```
VioletEyes-neo/                              ← 新分支根
├── apps/
│   ├── api/                                 ← NestJS 后端（迁移自 ）
│   ├── web/                                 ← React + Vite 前端（视觉重构自 ）
│   └── agent/                               ← Python Agent Runtime（包装 VioletEyes scripts）
├── packages/
│   ├── shared/                              ← 跨包 TS 枚举（覆盖 的 packages/shared）
│   ├── skill-schema/                        ← SKILL.md front-matter 的 JSON Schema（TS + Python 双实现）
│   └── report-theme/                        ← VioletEyes 视觉的 React 组件 + Tailwind preset
├── skills/                                  ← VioletEyes 原版 skill（v1.2.0 直接迁入）
│   ├── violeteyes-full/
│   ├── framework-detect/
│   ├── sink-detect/
│   ├── route-mapper/
│   ├── auth-audit/
│   └── supply-chain-cve/
├── docs/
│   └── platform/                            ← 本目录（01/02/03 + 历史）
├── docker-compose.yml
├── pnpm-workspace.yaml
└── README.md
```

### 1.2 模块依赖

```
apps/web ──▶ apps/api (HTTP /api/* + WS /scans)
              │
              ├──▶ Drizzle ORM ──▶ SQLite (WAL)
              ├──▶ BullMQ ──▶ Redis 7
              ├──▶ apps/agent (subprocess per scan)
              │       │
              │       └──▶ skills/*/SKILL.md (filesystem)
              │       └──▶ OSV.dev (HTTPS)
              │
              └──▶ packages/skill-schema (runtime validation)
```

### 1.3 进程边界

| 进程 | 数量 | 用途 |
|---|---|---|
| api (NestJS) | 1 | HTTP / WebSocket / Queue Worker / Bull-Board |
| web (nginx) | 1 | 静态资源 + 反代 `/api` + `/socket.io` |
| redis | 1 | BullMQ broker |
| agent-runtime | N（并发 1–10） | 由 api 通过 `child_process.spawn` 拉起，跑单个 scan |

Agent 跑在独立 Node 进程（Python 包装），通过 stdin/stdout NDJSON 协议与 api 通信。**LLM API key 只在 api 端**，agent 不直接调 LLM，所有 LLM 调用走 api 中转（保持密钥集中 + 可观测）。

---

## 2. 技术栈

### 2.1 后端 (apps/api)

| 类别 | 选型 | 版本 | 理由 |
|---|---|---|---|
| Runtime | Node.js | 20 LTS | 同  |
| Framework | NestJS | 10.4 | 同上 |
| ORM | Drizzle | 0.45+ | 同上，类型安全 + 轻量 |
| DB | SQLite (better-sqlite3) | 12.x | 同上；内测阶段足够；WAL 模式 |
| Queue | BullMQ | 5.x | 同上 |
| Real-time | socket.io | 4.8 | 同上 |
| Auth | @nestjs/jwt + passport-jwt + argon2 | latest | refresh token HttpOnly cookie |
| Validation | class-validator + class-transformer + zod | latest | 双保险：DTO class-validator + 关键路径 zod |
| Logging | pino | 9.x | 结构化日志 + 性能 |
| Metrics | @willsoto/nestjs-prometheus + prom-client | latest | 同  |
| Testing | vitest 2 + supertest | latest | 同  |
| AI | @anthropic-ai/sdk + openai + @openai/agents | latest | 多模型支持 |

### 2.2 前端 (apps/web)

| 类别 | 选型 | 版本 | 理由 |
|---|---|---|---|
| Framework | React | 18.3 | 同  |
| Build | Vite | 5.4 | 同上 |
| Router | react-router-dom | 7.x | 同上 |
| UI Primitives | Radix UI | latest | 同上 |
| Styling | Tailwind CSS | **4.x** | **是 3.4，本项目升 4** + VioletEyes preset |
| Icons | lucide-react | 0.469+ | 同上 |
| Markdown | react-markdown + remark-gfm + rehype-highlight | latest | 报告渲染 |
| Charts | **Chart.js + react-chartjs-2** | latest | **新增**：与 VioletEyes 报告风格一致 |
| Diagrams | **Mermaid** | latest | **新增**：调用链 |
| State | **Zustand** | 4.x | **新增**：替换 的 useState 散乱模式 |
| Data Fetch | **TanStack Query** | 5.x | **新增**：替换直接 fetch，统一缓存 + 乐观更新 |
| Forms | **react-hook-form + zod** | latest | **新增**：替换手写表单 |
| Toast | **sonner** | latest | **新增**：错误提示统一 |
| Testing | vitest 2 + @testing-library/react | latest | 同  |

### 2.3 Agent Runtime (apps/agent)

| 类别 | 选型 | 理由 |
|---|---|---|
| Language | Python | 3.11+，复用 VioletEyes v1.2 的所有 `scripts/*.py` |
| LLM 调用 | 通过 stdin NDJSON 由 api 中转（agent 不持 key） | 密钥集中 |
| Skill 解析 | packages/skill-schema（JSON Schema，TS + Python 双实现） | 跨进程一致性 |
| 文件系统 | `pathlib` + sandbox（`SandboxPath` 防止越界） | 借用  `code-tools.service.ts:92-304` 的思路 |
| 报告渲染 | Jinja2 调 `templates/*.j2`（从 VioletEyes v1.2 直接迁入） | 视觉一致性 |

### 2.4 选型理由（ vs VioletEyes-neo 差异）

| 项 |  | VioletEyes-neo | 理由 |
|---|---|---|---|
| Tailwind | 3.4 | **4.x** | VioletEyes 报告用 Tailwind v4 |
| 状态管理 | useState | Zustand | 多页面状态需要集中 |
| 数据请求 | 直接 fetch | TanStack Query | 缓存 + 重试 + 乐观更新 |
| 表单 | 手写 | react-hook-form | 校验统一 |
| 扫描 | vendor Python in-process | **独立 agent 子进程** | 隔离 + 可观测 + 可热替换 |

---

## 3. 数据模型

> Schema 详细 SQL 在 `apps/api/src/db/schema.ts`。下表是字段级语义，不是 DDL。

### 3.1 用户与认证

```
users
├── id            TEXT PK (usr-<randomHex(16)>)
├── username      TEXT UNIQUE NOT NULL
├── email         TEXT UNIQUE
├── passwordHash  TEXT (argon2id)
├── displayName   TEXT
├── role          ENUM('admin','auditor','viewer') DEFAULT 'auditor'
├── mustChangePassword BOOLEAN DEFAULT FALSE
├── lastLoginAt   INTEGER?
├── createdAt     INTEGER NOT NULL
└── updatedAt     INTEGER NOT NULL

refresh_tokens
├── id            TEXT PK (rt-<randomHex(32)>)
├── userId        TEXT FK → users.id
├── deviceLabel   TEXT?         ← 设备标签（用户填写）
├── userAgent     TEXT?
├── ip            TEXT?
├── expiresAt     INTEGER NOT NULL
├── revokedAt     INTEGER?
└── createdAt     INTEGER NOT NULL
```

> **修复点**：的 refresh_tokens 缺 device/UA/IP，本设计补齐。

### 3.2 项目

```
projects
├── id            TEXT PK (prj-<randomHex(12)>)
├── name          TEXT NOT NULL (≤128)
├── description   TEXT?
├── ownerId       TEXT FK → users.id
├── archivedAt    INTEGER?
├── createdAt     INTEGER NOT NULL
└── updatedAt     INTEGER NOT NULL

project_members
├── id            TEXT PK
├── projectId     TEXT FK → projects.id
├── userId        TEXT FK → users.id
├── role          ENUM('owner','editor','viewer')
├── invitedBy     TEXT FK → users.id
└── createdAt     INTEGER NOT NULL
```

### 3.3 代码版本

```
code_versions
├── id                TEXT PK (cv-<randomHex(12)>)
├── projectId         TEXT FK → projects.id
├── sourceType        ENUM('zip','git','github')
├── sourceRef         TEXT (URL or path)
├── commitSha         TEXT?             ← git 才有
├── storagePath       TEXT NOT NULL     ← /storage/code-versions/<id>/
├── sizeBytes         INTEGER
├── fileCount         INTEGER
├── locByLang         JSON (e.g. {"python": 12345})
├── status            ENUM('pending','ready','failed')
├── failureReason     TEXT?
├── sha256            TEXT NOT NULL
├── createdBy         TEXT FK → users.id
└── createdAt         INTEGER NOT NULL
```

### 3.4 Skill Bundle

```
skill_bundles                              ← skill 的"包"，可多个版本
├── id            TEXT PK (sb-<randomHex(12)>)
├── name          TEXT NOT NULL           ← rce-scanner
├── displayName   TEXT                    ← "RCE 专项扫描"
├── kind          ENUM('orchestrator','framework','entry-point','sink','vuln-class','supply-chain')
├── builtin       BOOLEAN                 ← VioletEyes 原版 = TRUE
├── description   TEXT
├── createdAt     INTEGER

skill_bundle_versions                      ← 一个 bundle 的具体版本
├── id            TEXT PK (sbv-<randomHex(16)>)
├── bundleId      TEXT FK → skill_bundles.id
├── version       TEXT NOT NULL
├── manifest      JSON NOT NULL           ← SKILL.md front-matter 解析后
├── manifestHash  TEXT NOT NULL           ← sha256(manifest) 防篡改
├── snapshotPath  TEXT NOT NULL           ← /storage/skills/<bundleId>/<version>/
├── sizeBytes     INTEGER
├── signature     TEXT?                   ← sha256:...（可选签名）
├── reviewStatus  ENUM('pending','approved','rejected')
├── reviewNote    TEXT?
├── reviewedBy    TEXT FK → users.id?
├── reviewedAt    INTEGER?
├── publishedAt   INTEGER?
├── isActive      BOOLEAN
├── isDefault     BOOLEAN                 ← 用于 Smart 模式决策
├── createdBy     TEXT FK → users.id
└── createdAt     INTEGER

project_skill_bindings                     ← 用户在项目里启用的 skill
├── id            TEXT PK
├── projectId     TEXT FK
├── bundleVersionId TEXT FK → skill_bundle_versions.id
├── enabled       BOOLEAN
├── enabledBy     TEXT FK → users.id
└── createdAt     INTEGER
```

> **修复点**：的 skill 硬编码在子仓库，本设计解耦为可上传、可审核、可绑定的实体。

### 3.5 扫描运行

```
scan_runs
├── id            TEXT PK (run-<randomHex(16)>)
├── projectId     TEXT FK
├── codeVersionId TEXT FK
├── triggeredBy   TEXT FK → users.id
├── scanMode      ENUM('quick','smart','deep','custom')
├── skillPlan     JSON NOT NULL           ← 实际加载的 skill 列表 + 决策理由
│   {                                       (Smart 模式才有 smart_decision 字段)
│     "skills": [
│       {"bundleVersionId": "sbv-...", "reason": "framework-matched:spring"},
│       ...
│     ],
│     "smartDecision": {                   ← only for SMART
│       "rationale": "...",
│       "rejectedSkills": [{"id":"...","reason":"framework-mismatch"}]
│     }
│   }
├── status        ENUM('queued','running','succeeded','failed','canceled')
├── startedAt     INTEGER?
├── finishedAt    INTEGER?
├── durationSec   INTEGER?
├── cost          JSON?                    ← {inputTokens, outputTokens, usd}
├── failureReason TEXT?
└── createdAt     INTEGER

skill_executions                            ← 每个 skill 在 scan 内的执行
├── id              TEXT PK
├── scanRunId       TEXT FK
├── bundleVersionId TEXT FK
├── skillName       TEXT
├── skillType       TEXT (kind)
├── executionStatus ENUM('not_run','initial_screened','partial','completed','not_applicable')
├── findingsStatus  ENUM('found','no_finding','pending_verification','environment_dependent')
├── primaryOutputs  JSON (string[])
├── dependsOn       JSON (string[])
├── traceRefs       JSON (string[])
├── exploitability  ENUM?
├── notes           TEXT?
├── startedAt       INTEGER
├── finishedAt      INTEGER?
└── durationSec     INTEGER?
```

### 3.6 Findings

```
findings
├── id            TEXT PK (find-<randomHex(16)>)
├── scanRunId     TEXT FK
├── bundleVersionId TEXT FK → skill_bundle_versions.id
├── skillName     TEXT
├── fingerprint   TEXT NOT NULL           ← sha256(file:line:cwe:snippet[:200])
├── title         TEXT
├── severity      ENUM('info','low','medium','high','critical')
├── cwe           TEXT? (e.g. "CWE-78")
├── vulnClass     TEXT?
├── filePath      TEXT
├── startLine     INTEGER
├── endLine       INTEGER
├── snippet       TEXT
├── callChain     JSON                    ← [{file, line, symbol, kind}, ...]
├── fixBefore     TEXT?
├── fixAfter      TEXT?
├── references    JSON (string[])
├── rawMetadata   JSON
└── createdAt     INTEGER

vulnerabilities                             ← 漏洞库（跨项目聚合）
├── id            TEXT PK
├── fingerprint   TEXT UNIQUE NOT NULL
├── title         TEXT
├── severity      ENUM
├── cwe           TEXT?
├── vulnClass     TEXT?
├── firstSeenAt   INTEGER
├── lastSeenAt    INTEGER
├── occurrenceCount INTEGER DEFAULT 1
├── status        ENUM('open','confirmed','ignored','fixed')
├── confirmedBy   TEXT FK → users.id?
├── confirmedAt   INTEGER?
├── ignoredBy     TEXT FK → users.id?
├── ignoredAt     INTEGER?
├── ignoreReason  TEXT?
├── fixedAt       INTEGER?
└── notes         TEXT?

finding_occurrences                         ← finding ↔ vulnerability 多对多
├── id            TEXT PK
├── findingId     TEXT FK
├── vulnId        TEXT FK
├── scanRunId     TEXT FK
└── createdAt     INTEGER
```

> **修复点**：的 `vuln-library.syncFromVulnerability` 状态错位 bug 已修——本设计用显式 status 字段。

### 3.7 报告

```
reports
├── id              TEXT PK (rep-<randomHex(16)>)
├── scanRunId       TEXT FK
├── format          ENUM('markdown','json','html','archive')
├── storagePath     TEXT
├── sizeBytes       INTEGER
├── generatedAt     INTEGER
└── generatedBy     TEXT FK → users.id
```

**报告 Token 成本展示（2026-06-30 决策）**：

扫描运行表 `scan_runs.cost` 字段（JSON）存储：
```json
{
  "inputTokens": 234567,
  "outputTokens": 45123,
  "totalTokens": 279690,
  "costUsd": 6.91,
  "byModel": {
    "claude-opus-4-8": {"inputTokens": 200000, "outputTokens": 40000, "costUsd": 6.00},
    "claude-haiku-4-5": {"inputTokens": 34567, "outputTokens": 5123, "costUsd": 0.91}
  },
  "bySkill": {
    "violeteyes-full": {"inputTokens": 180000, "outputTokens": 35000, "costUsd": 5.325},
    "rce-scanner": {"inputTokens": 20000, "outputTokens": 5000, "costUsd": 0.675}
  }
}
```

报告渲染时（HTML/Markdown/JSON）必须展示：
- HTML 报告：Cover 区添加 "Cost" 卡片，显示 `costUsd` + 分类图表
- Markdown 报告：§"执行概览"添加成本章节
- JSON 报告：原始 `cost` 字段透传
- 前端 Report 页面：顶部横幅显示 + 按 skill 拆分的 Chart.js 柱状图

### 3.8 Agent Trace

```
agent_traces
├── id              TEXT PK
├── scanRunId       TEXT FK
├── skillExecId     TEXT FK → skill_executions.id?
├── sequence        INTEGER
├── eventType       ENUM('llm.message','tool.call','tool.result','phase.transition','log','decision')
├── payload         JSON
├── inputTokens     INTEGER?
├── outputTokens    INTEGER?
├── costUsd         REAL?
├── createdAt       INTEGER
```

### 3.9 设置

```
settings                                   ← 单行 KV
├── key           TEXT PK
├── value         JSON
└── updatedAt     INTEGER

ai_keys                                     ← API Key 加密存储
├── id            TEXT PK
├── provider      ENUM('anthropic','openai','custom')
├── label         TEXT
├── apiKeyHint    TEXT                     ← "***xxxx"
├── apiKeyEnc     BLOB NOT NULL            ← AES-256-GCM(APP_MASTER_KEY, plaintext)
├── baseUrl       TEXT?
├── defaultModel  TEXT
├── availableModels JSON (string[])
├── isDefault     BOOLEAN
├── testStatus    ENUM('unknown','ok','failed')
├── testAt        INTEGER?
└── createdAt     INTEGER

git_credentials
├── id            TEXT PK
├── label         TEXT
├── host          TEXT
├── username      TEXT?
├── authType      ENUM('https_token','ssh_key')
├── tokenEnc      BLOB?
├── publicKeyEnc  BLOB?
├── privateKeyEnc BLOB?
├── fingerprint   TEXT NOT NULL
└── createdAt     INTEGER
```

---

## 4. API 表面

### 4.1 路由总览

| Method | Path | Guard | 说明 |
|---|---|---|---|
| POST | `/api/auth/login` | 公开 | usernameOrEmail + password |
| POST | `/api/auth/refresh` | cookie | refresh token 换新 access |
| POST | `/api/auth/logout` | cookie | 吊销 refresh |
| POST | `/api/auth/change-password` | JWT | 改密 + 吊销所有 refresh |
| GET | `/api/auth/me` | JWT | 当前用户 |
| GET | `/api/projects` | JWT | 列表（admin 全部，其余自己的） |
| POST | `/api/projects` | JWT | 创建 |
| GET | `/api/projects/:id` | JWT + member | 详情 |
| PATCH | `/api/projects/:id` | JWT + owner | 修改 |
| POST | `/api/projects/:id/archive` | JWT + owner | 归档 |
| POST | `/api/projects/:id/code-versions/upload` | JWT + editor | 上传 zip |
| POST | `/api/projects/:id/code-versions/from-git` | JWT + editor | Git URL |
| POST | `/api/projects/:id/code-versions/from-github` | JWT + editor | GitHub URL |
| GET | `/api/projects/:id/code-versions` | JWT + member | 列表 |
| GET | `/api/code-versions/:id` | JWT + member | 详情 |
| GET | `/api/skill-bundles` | JWT | 列表 |
| POST | `/api/skill-bundles/upload` | JWT + auditor | 上传 skill zip |
| GET | `/api/skill-bundles/:id` | JWT | 详情 |
| GET | `/api/skill-bundles/:id/versions` | JWT | 版本列表 |
| POST | `/api/skill-bundles/:id/versions/:versionId/review` | JWT + admin | 审核 |
| POST | `/api/skill-bundles/:id/versions/:versionId/publish` | JWT + admin | 发布 |
| POST | `/api/projects/:id/skill-bindings` | JWT + editor | 启用 skill |
| DELETE | `/api/projects/:id/skill-bindings/:bindingId` | JWT + editor | 停用 |
| POST | `/api/projects/:id/scan-runs` | JWT + editor | 创建扫描 |
| GET | `/api/scan-runs/:id` | JWT + member | 详情 |
| GET | `/api/scan-runs/:id/logs` | JWT + member | **修复**：加 Guard |
| GET | `/api/scan-runs/:id/skill-executions` | JWT + member | skill 执行 |
| GET | `/api/scan-runs/:id/findings` | JWT + member | findings |
| GET | `/api/scan-runs/:id/agent-traces` | JWT + member | trace |
| POST | `/api/scan-runs/:id/cancel` | JWT + editor | 取消 |
| GET | `/api/scan-runs/:id/report` | JWT + member | **修复**：加 Guard |
| GET | `/api/scan-runs/:id/report/archive` | JWT + member | zip 归档 |
| GET | `/api/projects/:id/vulns` | JWT + member | 项目漏洞库 |
| GET | `/api/vulnerabilities` | JWT | 全局漏洞库 |
| PATCH | `/api/vulnerabilities/:id` | JWT + editor | 改状态 |
| GET | `/api/projects/:id/vuln-trend` | JWT + member | **修复**：DB-side limit |
| GET | `/api/admin/users` | JWT + admin | 用户列表 |
| POST | `/api/admin/users` | JWT + admin | 创建用户 |
| PATCH | `/api/admin/users/:id` | JWT + admin | 修改 |
| GET | `/api/admin/settings/ai-keys` | JWT + admin | **修复**：加 admin guard |
| POST | `/api/admin/settings/ai-keys` | JWT + admin | 创建 |
| GET | `/api/admin/settings/git-credentials` | JWT + admin | **修复**：加 admin guard |
| GET | `/api/admin/queue-board` | JWT + admin | Bull-Board |
| GET | `/api/health` | 公开 | 健康检查 |
| GET | `/metrics` | 内部 | Prometheus |

### 4.2 WebSocket

```
namespace: /scans
auth: handleConnection 时校验 JWT cookie / query token
subscribe: scan:<runId>
events:
  phase.start       { phase, ts }
  phase.end         { phase, ts, summary }
  log.line          { level, msg, ts }
  finding.added     { finding }
  skill.started     { skillName }
  skill.finished    { skillName, status }
  run.status        { status, ts }
guard: 连接 + 订阅必须验证 user 对 runId 的读权限
```

> **修复点**：的 `origin:true` + 无 JWT 校验已修——本设计用 cookie + origin 白名单 + 订阅权限校验。

---

## 5. Skill 系统

### 5.1 Skill 包文件结构

```
my-skill.zip
├── SKILL.md                    ← 必需：YAML front-matter + Markdown 正文
├── README.md                   ← 可选：人类可读
├── signatures/                 ← 可选：特征库
│   └── *.md
├── payloads/                   ← 可选：sink 模式等
│   ├── sink-patterns.md
│   └── *.json
├── scripts/                    ← 可选：Python 辅助
│   └── *.py
└── examples/                   ← 可选
    └── *.md
```

### 5.2 SKILL.md 完整 Schema

> JSON Schema 落地在 `packages/skill-schema/src/skill-frontmatter.schema.json`，TS + Python 双实现。

```yaml
---
name: rce-scanner
displayName: "RCE 专项扫描"
version: 1.0.0
author: 
  name: "Cr1m3rA"
  email: "cr1m3ra@example.com"
license: Authorized-Testing-Only
description: "扫描命令注入、模板注入、代码注入等 RCE 类漏洞"

kind: vuln-class                 # orchestrator | framework | entry-point | sink | vuln-class | supply-chain

# 匹配条件（用于 Smart 模式决策 + 项目 skill 推荐）
targetLanguages: [python, java, javascript, typescript, go]
targetFrameworks: [django, flask, spring, express, fastapi, gin]
targetVulnClasses: [CWE-78, CWE-94, CWE-95]
targetManifests: [requirements.txt, pom.xml, package.json, go.mod]

# 输入输出契约
inputs:
  - name: source
    type: path
    required: true
    description: "代码版本落地路径"
  - name: severity_floor
    type: enum
    enum: [info, low, medium, high, critical]
    default: medium
  - name: max_findings
    type: integer
    default: 50
    min: 1
    max: 1000

outputs:
  - name: findings
    type: array
    schemaRef: ./finding-schema.json
  - name: summary
    type: object

# LLM 能力声明（决定可用 tool）
capability_modes:
  - name: quick
    tools_count: 4
    enables: [filesystem.read, grep.search, framework.detect]
  - name: deep
    tools_count: 12
    enables: [filesystem.read, filesystem.tree, grep.search, ast.grep, cve.lookup, framework.detect]

# MCP / 模型配置
mcp_dependencies: []
runtime:
  model: claude-opus-4-8
  temperature: 0.2
  max_tokens: 16384
  max_iterations: 30

# 元数据
tags: [security, code-audit, rce]
homepage: https://github.com/...
repository: https://github.com/...
---

# 这里是 skill 的执行指令（Markdown），由 LLM 读取
## 1. 侦察阶段
## 2. ...
```

### 5.3.1 Skill 上传与自动审核流程

**2026-06-30 决策**：第三方 skill 审核采用 **选项 C：自动 lint + 沙箱跑一遍**。admin 抽查为辅。

```
用户上传 skill.zip
  │
  ▼
SkillBundleService.upload(zip)
  │
  ├── 1. 基础校验：大小 ≤ 20MB / 文件数 ≤ 1000 / 解压比 ≤ 50
  ├── 2. 路径校验：no "..", no symlink, no executable bit
  │
  ▼
写入 skill_bundles + skill_bundle_versions（reviewStatus = 'pending'）
  │
  ▼
SkillAutoReviewService.review(versionId)
  │
  ├── 3. Lint 阶段
  │     ├── 解析 SKILL.md front-matter（packages/skill-schema）
  │     ├── 跑结构 lint：
  │     │     - 必填字段（name/version/kind/targetLanguages/...）
  │     │     - enum 校验（kind ∈ {orchestrator, framework, ...}）
  │     │     - 长度上限（name ≤ 64, description ≤ 1024）
  │     │     - capability_modes 工具白名单（仅允许声明的工具）
  │     │     - 危险模式检测（eval/exec/system/curl|wget 在 scripts/ 中）
  │     └── 输出 lintReport.json
  │
  ├── 4. 沙箱执行（仅当 lint 通过）
  │     ├── spawn 隔离 agent 子进程，限制：
  │     │     - filesystem: 只读 sandbox + 临时 /tmp（10MB 配额）
  │     │     - network: 默认 deny；可白名单 OSV.dev
  │     │     - exec: 禁止 child_process / os.system
  │     │     - timeout: 60s 强制
  │     │     - token 预算: 10k
  │     ├── 执行 scripts/* 的 --self-test --dry-run
  │     ├── 检查产出：exit 0 + 无 stderr + token 未超
  │     └── 输出 sandboxReport.json
  │
  ▼
reviewStatus =
  'approved'（lint + sandbox 都过）
  'pending'（任一失败，等待 admin 审查）
admin 可手动 'approved' 或 'rejected' + 留 note
```

**沙箱实现**：
- 复用 `apps/agent` 子进程 + LLM-API 中转
- 通过 stdin NDJSON 协议下发 `--self-test` 模式
- 文件系统隔离用 `bubblewrap`（Linux）/ `Job Objects`（Windows）；MVP 阶段用 chroot/容器降级
- 网络隔离用 nftables 规则（Linux）/ Windows Firewall

### 5.3 加载与执行流程

```
用户创建 scan_run
  │
  ▼
ScanService.create({ projectId, codeVersionId, scanMode, customSkillIds? })
  │
  ▼
SkillPlanner.resolve(run) ─── 决策 ────▶ SkillPlan { skills: [...], smartDecision?: {...} }
  │                                       │
  │                                       ▼
  │                                  写入 scan_runs.skillPlan
  ▼
ScanQueueService.enqueue(run)
  │
  ▼
ScanRunnerService.process(job) ── spawn ──▶ Agent Runtime (subprocess)
  │                                          │
  │                                          ├── 解析 skillPlan
  │                                          ├── 按顺序加载每个 skill
  │                                          ├── 通过 NDJSON 与 api 通信：
  │                                          │     { type: "llm.call", systemPrompt, messages, tools }
  │                                          │     ← { type: "llm.result", content, toolCalls, usage }
  │                                          │     { type: "tool.call", name, args }
  │                                          │     ← { type: "tool.result", result }
  │                                          │     { type: "event", eventType, payload }
  │                                          │
  │                                          └── 产出 findings.json / execution.log
  │
  ▼
ScanRunnerService.finalize(run)
  ├── 写 skill_executions 表
  ├── 写 findings + vulnerabilities + finding_occurrences
  ├── 触发 vulnerability.sync
  ├── 生成 reports (markdown/json/html/archive)
  └── 触发 WebSocket run.status = 'succeeded'
```

### 5.4 4 种扫描模式的 Skill 决策

| Mode | Planner 行为 |
|---|---|
| **QUICK** | `skills = project.enabledSkills ∩ user.selectedSkills`（用户勾选 + 项目启用）；**不加载** violeteyes-full |
| **SMART** | **不存在用户勾选**；LLM 自主从 `project.enabledSkills` 中挑选匹配的；violeteyes-full 强制加载；记录 `smartDecision.selectedSkills[]` + `rejectedSkills[]` + `rationale`（决策可审计、可回放） |
| **DEEP** | `skills = [violeteyes-full] ∪ project.enabledSkills`（全加载） |
| **CUSTOM** | `skills = user.selectedSkills`（用户完全控制）；**不自动加载** violeteyes-full |

**Smart 模式决策流程**：

```
1. ScanRunner 触发 Smart 模式
   │
2. 跑 Recon 阶段：framework-detect skill 产出 frameworkProfile.json
   │
3. Agent Runtime 调用 LLM（带 system_prompt + frameworkProfile + project.enabledSkills 列表）
   │
   ▼
   LLM 返回：
   {
     "selectedSkills": [{"id":"sbv-rce-...","reason":"framework-matched:spring, vuln-class:CWE-78"}, ...],
     "rejectedSkills": [{"id":"sbv-xxe-...","reason":"no-xml-parsing-detected"}, ...],
     "rationale": "目标为 Spring Boot 6.x REST API，启用 rce/ssrf/auth-audit，跳过 xxe/xxe-sast（无 XML 处理）"
   }
   │
4. 写入 scan_runs.skillPlan.smartDecision
5. 加载 violeteyes-full + LLM 选中的 skill 列表，按顺序执行
```

**关键约束**：
- LLM **只能从 `project.enabledSkills` 中挑选**，不允许加载未启用的 skill
- violeteyes-full 始终加载，LLM 不可跳过
- 决策必须完整记录，便于审计 + 优化 system prompt

### 5.5 内置 Skill

| Skill | Kind | 来源 |
|---|---|---|
| `violeteyes-full` | orchestrator | `skills/violeteyes-full/SKILL.md` —— 直接迁自 VioletEyes v1.2 `SKILL.md` |
| `framework-detect` | framework | 包装 `scripts/framework_detect.py` |
| `sink-detect` | sink | 包装 `scripts/sink_detect.py` |
| `route-mapper` | entry-point | 新写，跨框架 HTTP 入口识别 |
| `auth-audit` | vuln-class | 鉴权基线（修复  auth 相关漏洞） |
| `supply-chain-cve` | supply-chain | 包装 `scripts/cve_lookup.py` |

### 5.6 第三方 Skill 引导（社区可上传）

| Skill | 目标 |
|---|---|
| `rce-scanner` | CWE-78/94/95 |
| `ssrf-scanner` | CWE-918 |
| `sqli-scanner` | CWE-89 |
| `xxe-scanner` | CWE-611 |
| `deserialization-scanner` | CWE-502 |
| `xss-scanner` | CWE-79 |
| `path-traversal-scanner` | CWE-22 |
| `xxe-sast` | CWE-611 |

---

## 6. 视觉设计系统

### 6.1 设计 Token

```css
:root {
  /* VioletEyes 紫罗兰主题 */
  --violet-50:  #f5f3ff;
  --violet-100: #ede9fe;
  --violet-200: #ddd6fe;
  --violet-300: #c4b5fd;
  --violet-400: #a78bfa;
  --violet-500: #8b5cf6;
  --violet-600: #7c3aed;   /* 主色 */
  --violet-700: #6d28d9;   /* 强调 */
  --violet-800: #5b21b6;
  --violet-900: #4c1d95;
  --violet-950: #2e1065;

  /* Cover 渐变（from VioletEyes base.css） */
  --cover-gradient: linear-gradient(135deg, #4c1d95 0%, #1e1b4b 100%);
  --cover-radial: radial-gradient(ellipse at top, rgba(167,139,250,0.3), transparent 60%);

  /* 严重度色（与 VioletEyes 报告一致） */
  --sev-critical: #dc2626;   /* rose-600 */
  --sev-high:     #ea580c;   /* orange-600 */
  --sev-medium:   #ca8a04;   /* amber-600 */
  --sev-low:      #0891b2;   /* cyan-600 */
  --sev-info:     #64748b;   /* slate-500 */

  /* Slate 中性（与 VioletEyes 一致） */
  --slate-50:  #f8fafc;
  --slate-100: #f1f5f9;
  --slate-200: #e2e8f0;
  --slate-300: #cbd5e1;
  --slate-500: #64748b;
  --slate-700: #334155;
  --slate-900: #0f172a;

  /* 字体 */
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
}
```

### 6.2 Tailwind Preset

新增 `packages/report-theme/tailwind-preset.js`：

```js
module.exports = {
  theme: {
    extend: {
      colors: { violet: { /* 同上 */ } },
      fontFamily: { mono: ['JetBrains Mono', ...] },
      boxShadow: {
        'violet-glow': '0 0 24px rgba(124,58,237,0.4)',
      },
    },
  },
};
```

### 6.3 核心组件

| 组件 | 文件 | 说明 |
|---|---|---|
| `Logo` | `components/brand/Logo.tsx` | 8×8 渐变方块 + "VE"，hover 旋转 3° |
| `SeverityBadge` | `components/ui/SeverityBadge.tsx` | 圆形徽章 + 首字母 |
| `SeverityBar` | `components/ui/SeverityBar.tsx` | 左侧 4px 色条 + 卡片 |
| `Cover` | `components/brand/Cover.tsx` | 紫光径向 + 线性 + 网格纹理 + 毛玻璃徽章 |
| `Header` | `components/layout/Header.tsx` | `backdrop-blur bg-white/80` + sticky |
| `Chart` | `components/ui/Chart.tsx` | 环形图 + 水平柱状图（Chart.js 包装） |
| `Mermaid` | `components/ui/Mermaid.tsx` | 调用链渲染 |
| `CallChainTabs` | `components/ui/CallChainTabs.tsx` | 树形文本 + Mermaid 双 Tab |
| `FixDiff` | `components/ui/FixDiff.tsx` | Before/After 双列（红/绿 header） |

### 6.4 页面清单（重构自 ）

| 路由 | 说明 | 视觉重点 |
|---|---|---|
| `/login` | 登录 | 紫光背景 + Logo + 毛玻璃表单 |
| `/` (Home) | 仪表盘 | 项目卡 + 最近扫描 + 严重度环图 |
| `/projects` | 项目列表 | 紫罗兰卡片网格 |
| `/projects/:id` | 项目详情 | Tab：Overview / CodeVersions / Scans / Vulns / Skills / Members |
| `/projects/:id/scans/:runId` | 扫描详情 | 阶段进度条 + 实时日志 + skill 执行卡片 |
| `/projects/:id/scans/:runId/report` | 报告 | **复用 VioletEyes 模板**，紫罗兰主题 |
| `/projects/:id/skills` | skill 管理 | 上传 + 列表 + 启用 toggle |
| `/vulns` | 全局漏洞库 | 趋势图 + 表格 + 状态批量操作 |
| `/traces/:scanId` | Agent Trace | 时间线 + 折叠消息 + token 统计 |
| `/settings` | 个人设置 | 改密 + AI Key + Git 凭证 |
| `/admin/users` | 用户管理 | 表格 + 角色编辑 |
| `/admin/skills` | skill 审核 | pending 列表 + 通过/拒绝 |

---

## 7. Agent Runtime

### 7.1 进程协议（NDJSON over stdin/stdout）

api → agent（一行 JSON）：
```json
{"type":"init","scanRunId":"run-...","codeVersionPath":"/storage/...","skillPlan":{...}}
{"type":"llm.call","requestId":"r-1","systemPrompt":"...","messages":[...],"tools":[...]}
{"type":"cancel"}
```

agent → api：
```json
{"type":"ready"}
{"type":"llm.result","requestId":"r-1","content":"...","toolCalls":[...],"usage":{"input":1234,"output":567,"usd":0.05}}
{"type":"event","eventType":"finding.added","payload":{...}}
{"type":"event","eventType":"log.line","payload":{"level":"info","msg":"..."}}
{"type":"done","summary":{...}}
{"type":"error","message":"...","stack":"..."}
```

### 7.2 启动参数

```python
# apps/agent/main.py
if __name__ == '__main__':
    agent = AgentRuntime()
    agent.run()  # 阻塞 stdin 循环
```

api spawn：
```ts
const child = spawn('python3', ['apps/agent/main.py'], {
  env: { ...process.env, AGENT_RUN_ID: runId, AGENT_STORAGE: '/storage/code-versions/...' },
  stdio: ['pipe', 'pipe', 'pipe'],
});
```

### 7.3 工具集（Tool Definitions）

agent 可用工具（包装后转发到 api 端执行）：

| Tool | 说明 | 后端实现 |
|---|---|---|
| `filesystem.read` | 读单文件 | api 端 `SandboxPath` 校验 |
| `filesystem.tree` | 列目录 | 同上 |
| `grep.search` | ripgrep | 同上 |
| `ast.grep` | ast-grep | 同上（可选） |
| `framework.detect` | 调用 framework_detect.py | api 端 spawn |
| `cve.lookup` | OSV.dev 查询 | api 端 + 离线缓存 |
| `web.fetch` | 抓 URL | **可选**（admin 启用） |
| `code.search` | 跨文件符号搜索 | 同 filesystem |

---

## 8. 安全模型

### 8.1 认证

| 场景 | 实现 |
|---|---|
| 登录 | bcrypt/argon2 验密 → 签 access (15min) + refresh (7d, HttpOnly) |
| access | 内存保存（React state + Zustand，**不** localStorage） |
| refresh | HttpOnly + Secure + SameSite=Lax cookie |
| API 调用 | Authorization: Bearer <access> |
| WebSocket | cookie 自动带 |
| 改密 | 必须验旧密 + 校验强度 + 吊销**所有** refresh |
| 登出 | 调 `/api/auth/logout` 吊销当前 refresh |

### 8.2 授权

- `JwtAuthGuard` 全局（除显式 `@Public()`）
- `RolesGuard` 全局，按 `@Roles('admin')` 装饰
- `ProjectRoleGuard` 自定义，按项目成员 + 角色

### 8.3 输入校验

| 入口 | 校验 |
|---|---|
| 所有 Body | `ValidationPipe({ whitelist: true, forbidNonWhitelisted: true, transform: true })` |
| 所有 Query | zod schema（关键路径） |
| 所有 Param | class-validator |
| zip 上传 | size ≤ 500MB + 解压比 ≤ 100 + 文件数 ≤ 100k + 单文件 ≤ 100MB + 无 `..` 路径 + 无符号链接 |
| Git URL | scheme ∈ {https, ssh} + host 白名单 + 端口限制 |
| SKILL.md | 大小 ≤ 256KB + front-matter 必须 schema 通过 + 文件数 ≤ 1000 |
| skill zip | 大小 ≤ 20MB + 解压比 ≤ 50 + 无可执行权限 |

### 8.4 密钥管理

- `JWT_SECRET` / `APP_MASTER_KEY` / `SESSION_SECRET` 启动校验长度 ≥ 32 且熵足（不同字符数 ≥ 16）
- 默认值（如 `change-me-...`）启动时 `throw`，拒启动
- AI Key 落库前 `AES-256-GCM(APP_MASTER_KEY, plaintext)`
- 内存中 agent 不持密钥

### 8.5 修复清单（追溯到 §6）

| Bug | 本设计修复 |
|---|---|
| `/api/scan-runs/:id/report` 缺 Guard | `JwtAuthGuard` 全局 |
| `/api/scan-runs/:id/logs` 缺 Guard | 同上 |
| Socket.IO 开放 | cookie auth + origin 白名单 + 订阅权限 |
| token localStorage | 内存 + refresh HttpOnly |
| updatePassword 不验强度 | `validatePasswordStrength` |
| zip 上传缺 project membership | `ProjectRoleGuard('editor')` |
| zip-bomb 防护 | §8.3 校验 |
| 登录不支持 email | `or(eq(username), eq(email))` |
| 默认密钥无校验 | 启动校验 |
| LIKE 通配符注入 | zod 参数化 + LIKE 转义 |
| randomHex 用 Math.random | `crypto.randomBytes` |
| scanLogs Map 泄漏 | try/finally |
| vuln-library 状态错 | 显式 status 字段 |
| JWT expiresIn 不一致 | 统一 15min + service 一致 |

---

## 9. 可观测性

### 9.1 Prometheus 指标

```
violeteyes_scan_runs_total{mode, status}
violeteyes_scan_duration_seconds{mode, status}
violeteyes_scan_findings_total{severity, cwe}
violeteyes_skill_execution_duration_seconds{skill_name, status}
violeteyes_llm_tokens_total{provider, model, kind}
violeteyes_llm_cost_usd_total{provider, model}
violeteyes_queue_size{queue}
violeteyes_active_agents
violeteyes_http_requests_total{method, route, status}
violeteyes_http_request_duration_seconds{method, route}
```

### 9.2 日志

```json
{"level":"info","ts":"2026-06-30T12:34:56.789Z","runId":"run-...","userId":"usr-...","phase":"recon","msg":"framework detected","framework":"spring-boot","cost":{"input":1234,"output":567}}
```

### 9.3 健康检查

```
GET /api/health
{
  "status": "ok",
  "checks": {
    "db": "ok",
    "redis": "ok",
    "aiKey": { "provider": "anthropic", "status": "ok" }
  }
}
```

---

## 10. 部署

### 10.1 docker-compose.yml 服务

| 服务 | 镜像 | 端口 | 卷 |
|---|---|---|---|
| api | `violeteyes-neo-api:latest` | 127.0.0.1:3030 → 3000 | `./storage:/app/storage` |
| web | `violeteyes-neo-web:latest` | 127.0.0.1:8090 → 80 | — |
| redis | redis:7-alpine | （内部） | redis-data |

### 10.2 环境变量

```
NODE_ENV=production
PORT=3000
DATABASE_URL=/app/storage/violeteyes.db
REDIS_HOST=redis
REDIS_PORT=6379
JWT_SECRET=<32+ chars, high entropy>
APP_MASTER_KEY=<32+ chars, high entropy>
SESSION_SECRET=<32+ chars, high entropy>
CORS_ORIGINS=https://violeteyes.local
SCAN_MAX_CONCURRENT=3
LOG_LEVEL=info
SKILL_BUNDLE_DIR=/app/storage/skills
CODE_VERSION_DIR=/app/storage/code-versions
```

### 10.3 CI（.github/workflows/ci.yml）

1. install (pnpm)
2. typecheck (tsc --noEmit)
3. test (vitest run --coverage)
4. lint (eslint)
5. build (api + web)
6. docker build (api + web)

---

## 11. 模块边界与依赖图

```
apps/api/src/
├── main.ts                              # 启动 + global pipes/guards
├── app.module.ts
├── common/
│   ├── crypto.util.ts                   # AES-256-GCM, scrypt, key strength check
│   ├── sandbox-path.ts                  # 路径越界防护
│   ├── pagination.dto.ts
│   └── errors/
├── db/
│   ├── schema.ts                        # 所有表定义
│   ├── database.module.ts
│   ├── migrations/
│   └── seed.ts
├── auth/
│   ├── auth.{controller,service,module}.ts
│   ├── jwt.strategy.ts
│   ├── jwt-auth.guard.ts                # GLOBAL
│   ├── roles.{decorator,guard}.ts       # GLOBAL
│   ├── public.decorator.ts
│   └── current-user.decorator.ts
├── users/
├── projects/
├── code-versions/
├── skill-bundles/
├── skill-bindings/
├── scan/
│   ├── scan.{controller,service,module}.ts
│   ├── scan-queue.service.ts            # BullMQ
│   ├── scan-runner.service.ts           # spawn agent subprocess
│   ├── scan-planner.service.ts          # mode → skill plan
│   ├── scan-orchestrator.client.ts      # NDJSON 协议
│   ├── scan-coverage.service.ts
│   ├── tools/
│   │   ├── filesystem.tools.ts
│   │   ├── grep.tools.ts
│   │   ├── ast.tools.ts
│   │   ├── framework.tools.ts
│   │   └── cve.tools.ts
│   └── coverage.util.ts
├── skill-execution/
├── vulns/
├── vulnerabilities/                     # 漏洞库
├── reports/
│   ├── markdown.report.ts
│   ├── json.report.ts
│   ├── html.report.ts                   # 调 Jinja2 via agent subprocess
│   └── archive.report.ts
├── agent-traces/
├── realtime/scan.gateway.ts             # 修复：cookie auth + origin 白名单
├── settings/
│   ├── ai-keys.{controller,service}
│   └── git-credentials.{controller,service}
├── admin/
│   ├── users.{controller,service}
│   ├── skills-review.{controller,service}
│   └── queue-board/
├── health/
└── metrics/

apps/agent/                              # Python Agent Runtime
├── main.py                              # NDJSON stdin loop
├── llm_client.py                        # 调 api 中转（via stdin 协议）
├── skill_loader.py
├── skill_runner.py
├── tools/
└── report/                              # 复用 VioletEyes templates/*.j2

packages/skill-schema/
├── src/
│   ├── frontmatter.schema.json
│   ├── index.ts                         # zod-derived
│   ├── py/                              # Python 等价实现
│   │   └── frontmatter_schema.py
└── index.spec.ts

packages/shared/
├── src/
│   ├── enums.ts                         # severity / cwe / status ...
│   └── finding-schema.ts
└── index.spec.ts

packages/report-theme/
├── src/
│   ├── tailwind-preset.js
│   ├── components/
│   └── tokens.css
└── ...
```

---

## 12. 关键决策记录（ADR）

| 决策 | 选项 | 选择 | 理由 |
|---|---|---|---|
| Tailwind 版本 | 3.4 vs 4.x | 4.x | VioletEyes 报告用 v4；API 更现代 |
| 状态管理 | useState vs Zustand | Zustand | 多页面跨组件状态需要 |
| 数据请求 | fetch vs TanStack Query | TanStack Query | 缓存 + 重试 + 乐观更新 |
| Agent 进程 | in-process vs subprocess | subprocess | 隔离 + 失败不影响 api |
| LLM 调用 | agent 直连 vs api 中转 | api 中转 | 密钥集中 + 可观测 |
| Skill 包格式 | zip vs git repo vs OCI | zip | 易用；解压即用 |
| Skill 签名 | 必选 vs 可选 | 可选 | 强制会阻碍 MVP 推广 |
| DB | SQLite vs PostgreSQL | SQLite | 内测足够；可后续迁移 |
| 视觉来源 | VioletEyes 模板 vs 重写 | 复用模板 | 视觉一致性 |
| 报告渲染 | 后端 vs 前端 | 后端 (api → agent Jinja2) | 与 VioletEyes 报告字节级一致 |

---

## 13. 文档索引

- 需求 → [01-requirements.md](./01-requirements.md)
- 计划 → [03-development-plan.md](./03-development-plan.md)
- VioletEyes 原版 skill → `../../SKILL.md`
- VioletEyes 视觉规范 → `../05-html-report.md`
-  bug 探索 → §6 / 安全规范