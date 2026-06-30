# VioletEyes-neo 需求文档（Requirements）

> 版本：0.1.0-draft · 日期：2026-06-30 · 状态：业务可行性测试需求草案
> 文档目标读者：产品 / 安全研发 / 架构师 / 项目 Owner
> 与本文档配套的还有 [02-specification.md](./02-specification.md) 和 [03-development-plan.md](./03-development-plan.md)

---

## 0. 项目背景

### 0.1 现状盘点

| 项目 | 现状 | 关键局限 |
|---|---|---|
| **VioletEyes** v1.2.0（`C:\Users\Jerome\Documents\VioletEyes`） | LLM Agent Skill，5 阶段流水线，10+ 语言、70+ 框架、56 种漏洞类型，单文件离线 HTML 报告 | 不是 Web 应用；无项目/用户/协作概念；扫描入口强依赖 Agent 框架（Claude Code/Cline/Cursor）；skill 替换不友好（需要直接改 `SKILL.md`） |
| **** | NestJS+React+SQLite+BullMQ+OpenAI Agents 的 Web 审计平台，17 张表、12 个页面、38 个 vendor Skill | 仅 .NET 扫描；多语言仅做 LOC 计数；鉴权、异常处理、性能、UI 上存在大量已知 bug（详见 §6）；视觉风格与 VioletEyes 不一致；不支持 skill 拓展 |

### 0.2 一句话定位

**VioletEyes-neo** = VioletEyes 的审计能力 + 的工程化形态 → 一个**多语言、可扩展、Web 化**的代码审计测试平台，向用户暴露 VioletEyes 风格的可视化与交互。

### 0.3 业务可行性测试目标

本仓库以 **业务可行性测试**（business feasibility test）为目的发起，不代表已承诺上线。测试聚焦四个问题：

1. 是否有足够用户愿意"上传代码 → 选择 skill 组合 → 拿到一份漂亮的审计报告"？
2. "智能选择 skill"在真实仓库上的准确率/召回率/误报率是否能支撑付费？
3. 多 skill 编排的开销（token、时长、成本）是否在用户可接受范围内？
4. VioletEyes 视觉风格 + Web 平台形态能否支撑差异化定位？

> 代码与应用**功能完整、可独立运行**，但所有架构/性能/安全决策都按"小规模内测 50–200 用户"做上限假设。

---

## 1. 范围与边界

### 1.1 In-Scope（MVP 必做）

| # | 能力 | 说明 |
|---|---|---|
| F1 | 多语言代码审计 | Java/JS/TS/Python/Go/PHP/Ruby/C#/Rust/Vue/React，至少在 6 种语言上跑通端到端 |
| F2 | 项目/代码版本管理 | Web UI 创建项目、上传 zip、Git clone、GitHub clone |
| F3 | 4 种扫描模式 | Quick / Smart / Deep / Custom（见 §3.2） |
| F4 | Skill 拓展系统 | 用户可导入、启用、停用、删除 skill；skill 包用 zip 上传 |
| F5 | 报告 | Markdown + JSON + HTML（复用 VioletEyes 报告模板）+ 归档 zip |
| F6 | 用户与权限 | 用户注册/登录/角色（admin / auditor / viewer） |
| F7 | 实时进度 | WebSocket 推送扫描阶段、日志、tool 调用、findings 增量 |
| F8 | 漏洞库 | 历史 findings 聚合、按 CWE/严重度统计、趋势图、忽略/确认状态 |
| F9 | 审计追踪 | Agent Trace：完整保存 tool call、LLM message、token 消耗 |
| F10 | VioletEyes 视觉 | 紫罗兰主题、`#7c3aed` 主色、严重度色条、Chart.js + Mermaid |

### 1.2 Out-of-Scope（本期不做）

- 黑盒联动（ShadowFox）—— 仅预留接口
- 实时协作 / 多用户同审
- 第三方漏洞库（NVD/VulnCheck）—— 复用 VioletEyes V1.2 的 OSV 离线缓存
- 商业版付费墙、发票、SSO
- iOS/Android/CLI 客户端

### 1.3 非目标（Non-goals）

- **不做** AST 级精确污点追踪 —— VioletEyes 是 LLM-driven Skill，可信度依赖 LLM + 正则 hybrid，精度天花板与 v1.2.0 持平
- **不做** 替换 SonarQube / Snyk 之类的传统 SAST —— VioletEyes-neo 是 LLM-Skill 编排器，不是工业级 SAST
- **不做** 多租户隔离 —— 内测阶段单实例运行，所有用户数据共用一个 SQLite

---

## 2. 用户角色与场景

### 2.1 角色（Role）

| 角色 | 典型动作 | 权限 |
|---|---|---|
| **admin** | 平台配置、AI Key 管理、用户管理、Skill 审核 | 全部 |
| **auditor** | 创建项目、发起扫描、查看报告、导入 skill | 项目读写；admin 配置只读 |
| **viewer** | 查看报告与漏洞库 | 项目只读 |

### 2.2 关键场景

#### 场景 A：审计师日常（happy path）

```
1. auditor 登录 → 进入"我的项目" → 新建项目 "Acme-Payment"
2. 上传代码 zip（或粘贴 GitHub URL）
3. 在扫描模式里选 "Smart" → 一键启动
4. 实时看 WebSocket 推送的进度条和阶段日志
5. 扫描结束 → 自动生成报告 → 下载 HTML / Markdown / 归档
6. 把 3 个高危漏洞标记为"已确认"，其余标"忽略"
7. 在漏洞库里看跨项目的趋势
```

#### 场景 B：深度审计（Deep）

```
1. auditor 创建项目 "Acme-Payment"
2. 选 Deep 模式 → 系统强制加载 VioletEyes 原版 skill + 所有已启用的扩展 skill
3. 预计耗时 30–120 分钟（取决于仓库规模）
4. 报告含完整调用链 + 修复对比 + CVE 依赖扫描
```

#### 场景 C：专项审计（Quick + Custom）

```
1. auditor 只想查 RCE
2. 选 Quick 模式 + 勾选 "RCE 扫描" skill
3. 5 分钟内出结果
```

#### 场景 D：skill 拓展

```
1. auditor 从 GitHub 下载 "violeteyes-skill-ssrf.zip"
2. 在 Skill 中心上传 zip → 系统解析 manifest → 校验签名 → 启用
3. 后续扫描中可勾选该 skill
```

#### 场景 E：admin 配置

```
1. admin 配置 OpenAI / Anthropic Key
2. admin 设置扫描并发上限、token 预算
3. admin 审核用户上传的 skill
```

---

## 3. 功能需求

### 3.1 项目管理（F1–F2）

| ID | 需求 | 优先级 |
|---|---|---|
| FR-PROJ-01 | 用户可创建项目，必填字段 `name`（≤128 字符）+ 可选 `description` | P0 |
| FR-PROJ-02 | 项目支持归档（`archivedAt`），归档后只读 | P0 |
| FR-PROJ-03 | 项目成员：owner / editor / viewer 三种角色，admin 跨项目可见 | P0 |
| FR-PROJ-04 | 代码版本支持 zip 上传、Git URL、GitHub URL 三种来源 | P0 |
| FR-PROJ-05 | 上传 zip 必须做解压炸弹（zip-bomb）防护：限制解压前/后比率、单文件最大体积、解压文件总数 | P0 |
| FR-PROJ-06 | Git URL 必须做白名单校验，禁止 `file://` / `git://`，限制端口与主机 | P0 |
| FR-PROJ-07 | 代码版本落地后必须做 SHA-256 校验，落地失败可重试 | P1 |

### 3.2 扫描模式（F3）

| 模式 | 加载策略 | 适用场景 | 预计耗时 | 预计 token |
|---|---|---|---|---|
| **Quick** | 仅使用用户**已勾选**的 skill；不加载 VioletEyes 原版 | 已知只想查某类问题（如只查 RCE） | < 5 分钟 | < 50k |
| **Smart** | **不存在用户勾选**；LLM 自行从 `project.enabledSkills` 中决定加载哪些 skill + VioletEyes 原版强制加载 | 默认日常审计（VioletEyes 核心价值） | 10–30 分钟 | 100k–300k |
| **Deep** | 强制加载 VioletEyes 原版 skill + **所有**用户启用的扩展 skill | 立项前深度审计、发布前闸口 | 30–120 分钟 | 300k–800k |
| **Custom** | 用户勾选具体 skill 列表，可任意组合、任意顺序；不自动加载原版 | 已知问题复现、特定规则验证 | 5–60 分钟 | 用户决定 |

**关键约束**：

- **VioletEyes 原版 skill 必须始终存在**，不能被删除；可"禁用"但不删
- 模式映射到 `ScanRun.scanMode` enum：`QUICK / SMART / DEEP / CUSTOM`
- **Smart 模式决策规则（2026-06-30 拍板）**：
  - **不存在用户勾选**——Smart 模式下用户不预先选择 skill，由 LLM 基于 Recon 阶段的 `frameworkProfile` + `assets.json` 自主决定
  - LLM 从 `project.enabledSkills`（用户在项目里启用的 skill 集合）中挑选匹配的
  - violeteyes-full 强制加载，不可被 LLM 跳过
  - 决策必须记录到 `smart_decision.json`，包含 `selectedSkills[{id, reason}]` + `rejectedSkills[{id, reason}]` + `rationale`
  - 决策可审计、可回放，便于后续优化 system prompt
- 模式 + skill 列表写入 `execution.log`（审计可追溯）

### 3.3 Skill 拓展系统（F4）

#### 3.3.1 Skill 包结构

延续 VioletEyes 的 `SKILL.md` YAML front-matter 风格，但加严格 schema：

```yaml
---
name: rce-scanner
displayName: "RCE 专项扫描"
version: 1.0.0
author: Cr1m3rA <...>
license: Authorized-Testing-Only
kind: vuln-class            # framework | entry-point | sink | vuln-class | supply-chain | orchestrator
targetLanguages: [python, java, javascript, typescript, go]
targetFrameworks: [django, flask, spring, express, fastapi]
targetVulnClasses: [CWE-78, CWE-94]
inputs:
  - { name: source, type: path, required: true }
  - { name: severity_floor, type: enum, enum: [info, low, medium, high, critical], default: medium }
outputs:
  - { name: findings, type: array, schema: finding-schema.json }
capability_modes:
  - { name: quick, tools_count: 4, enables: [filesystem, grep] }
  - { name: deep,  tools_count: 12, enables: [filesystem, grep, ast-grep, cve_lookup] }
mcp_dependencies: []
runtime:
  model: claude-opus-4-8      # 可选，覆盖默认
  temperature: 0.2
  max_tokens: 16384
signature: "sha256:..."        # zip 上传时强制校验
---
# 这里是 skill 的执行指令（Markdown），由 LLM 读取
```

#### 3.3.2 Skill 加载流程

1. **上传**：用户在 Skill 中心上传 zip（含 `SKILL.md` + 可选 `signatures/` / `payloads/` / `scripts/`）
2. **校验**：后端做 manifest 校验 + 签名校验 + 大小限制（≤ 20MB）+ path 越界检查
3. **入库**：写入 `skill_bundles` + `skill_bundle_versions` 表
4. **审核**：admin 可标记 `approved/rejected`
5. **启用**：用户在自己的项目里启用/停用 skill
6. **执行**：扫描时由 `SkillExecutorService` 按模式加载

#### 3.3.3 内置 Skill（开箱即用）

| Skill | Kind | 说明 |
|---|---|---|
| `violeteyes-full` | orchestrator | VioletEyes 原版，全量流水线（**不可删除**） |
| `framework-detect` | framework | 框架/入口识别（继承自 `scripts/framework_detect.py`） |
| `sink-detect` | sink | 正则 sink 匹配（继承自 `scripts/sink_detect.py`） |
| `route-mapper` | entry-point | HTTP 入口识别（跨框架） |
| `auth-audit` | vuln-class | 鉴权基线 |
| `supply-chain-cve` | supply-chain | OSV.dev 联网查询 + 离线缓存 |

#### 3.3.4 第三方 Skill 示例（社区可上传）

| Skill | 目标 |
|---|---|
| `rce-scanner` | CWE-78/94 |
| `ssrf-scanner` | CWE-918 |
| `sqli-scanner` | CWE-89 |
| `xxe-scanner` | CWE-611 |
| `deserialization-scanner` | CWE-502 |
| `xxe-sast` | CWE-611 |

### 3.4 报告（F5）

| 需求 | 说明 |
|---|---|
| FR-REPORT-01 | Markdown 报告：聚合所有 skill 的 findings，章节结构固定 |
| FR-REPORT-02 | JSON 报告：原始 findings（与 `finding-schema.json` 对齐） |
| FR-REPORT-03 | HTML 报告：直接复用 `templates/base.html.j2` 渲染管线（紫罗兰主题） |
| FR-REPORT-04 | 归档 zip：code version + findings + report + execution.log |
| FR-REPORT-05 | 报告里必须包含：调用链 Mermaid 图、修复 Before/After、严重度环形图、Top 10 漏洞类型 |
| FR-REPORT-06 | 报告下载必须鉴权（`JwtAuthGuard` + project membership） |

### 3.5 用户与权限（F6）

| 需求 | 说明 |
|---|---|
| FR-USER-01 | username + password 登录，access token **必须放内存**、refresh token HttpOnly cookie（修复 的 localStorage bug） |
| FR-USER-02 | 支持 username 或 email 登录（目前仅支持 username，是 bug） |
| FR-USER-03 | `updatePassword` 必须验旧密码 + 校验强度 + 吊销旧 refresh token |
| FR-USER-04 | 角色 admin/auditor/viewer，admin 跨项目可见 |
| FR-USER-05 | 默认 admin 账号首次登录必须强制改密 |

### 3.6 实时进度（F7）

| 需求 | 说明 |
|---|---|
| FR-RT-01 | WebSocket 命名空间 `/scans`，订阅 `scan:{runId}` 频道 |
| FR-RT-02 | 事件类型：`phase.start / phase.end / log.line / finding.added / run.status` |
| FR-RT-03 | 连接必须 JWT 鉴权（修复 的开放 CORS bug） |
| FR-RT-04 | 订阅必须验证当前用户对该 runId 的读权限 |

### 3.7 漏洞库（F8）

| 需求 | 说明 |
|---|---|
| FR-LIB-01 | 同一 `fingerprint`（hash of file+line+cwe+snippet）的 finding 在漏洞库自动合并 |
| FR-LIB-02 | 状态：`open / confirmed / ignored / fixed` |
| FR-LIB-03 | 跨项目趋势：按 CWE、按 severity、按周/月聚合 |
| FR-LIB-04 | `vuln-library.syncFromVulnerability` 的状态错位 bug 必须修复（ §6.4.2） |

### 3.8 审计追踪（F9）

| 需求 | 说明 |
|---|---|
| FR-TRACE-01 | 每条 LLM message、tool call、token 消耗都必须持久化 |
| FR-TRACE-02 | 必须在 Agent Trace 页面可视化回放 |
| FR-TRACE-03 | 私有 skill 的 prompt 也只对 admin 可见（避免泄露） |

---

## 4. 非功能需求（NFR）

### 4.1 安全

| ID | 需求 | 严重 |
|---|---|---|
| NFR-SEC-01 | 所有 `/api/*` 必须 `JwtAuthGuard`，例外仅 `/api/auth/*`、`/api/health` | 阻断 |
| NFR-SEC-02 | 所有 `/api/admin/*` 必须 `Roles('admin')` | 阻断 |
| NFR-SEC-03 | WebSocket 必须 JWT 鉴权 + origin 白名单 | 阻断 |
| NFR-SEC-04 | zip-bomb 防护、path 越界防护（`safeExtractZip`）、Git URL 白名单 | 阻断 |
| NFR-SEC-05 | access token 内存保存；refresh token HttpOnly + Secure + SameSite=Lax | 阻断 |
| NFR-SEC-06 | `JWT_SECRET`、`APP_MASTER_KEY`、`SESSION_SECRET` 启动时必须校验长度 ≥ 32 且熵足，否则拒启动 | 阻断 |
| NFR-SEC-07 | `LIKE` 查询必须参数化；禁止字符串拼接通配符（ §6.4.5 bug） | 高 |
| NFR-SEC-08 | `randomHex` 必须用 `crypto.randomBytes`（ §6.4.5 bug） | 高 |
| NFR-SEC-09 | `SKILL.md` 大小限制 ≤ 256KB（防止 prompt injection） | 高 |
| NFR-SEC-10 | skill 上传 zip 大小限制 ≤ 20MB，文件数 ≤ 1000 | 高 |

### 4.2 性能

| ID | 需求 | 目标 |
|---|---|---|
| NFR-PERF-01 | 报告 Markdown 渲染 | < 3s（P95，10MB finding 集合） |
| NFR-PERF-02 | 扫描任务并发 | 默认 3 路，可配置 1–10 |
| NFR-PERF-03 | 单次扫描超时 | 24h 强制终结 |
| NFR-PERF-04 | WebSocket 事件吞吐 | 每秒 ≥ 100 事件不丢 |
| NFR-PERF-05 | SQLite WAL checkpoint | 每 100MB 触发 |
| NFR-PERF-06 | 漏洞库 trend 查询 | 必须 DB-side limit + where（修复  §6.4.5 bug） |
| NFR-PERF-07 | `scanLogs` / `runningScans` Map 必须在异常路径也清理（修复内存泄漏） | 高 |

### 4.3 可观测性

| ID | 需求 |
|---|---|
| NFR-OBS-01 | Prometheus 指标：扫描并发、token 消耗、findings 计数、skill 执行耗时 |
| NFR-OBS-02 | Bull-Board 队列可视化（admin only） |
| NFR-OBS-03 | 结构化日志（pino），每条记录含 `runId / userId / phase / cost` |
| NFR-OBS-04 | 健康检查 `/api/health` 含 DB、Redis、AI Key 校验 |

### 4.4 可用性

| ID | 需求 |
|---|---|
| NFR-UX-01 | 首屏加载 ≤ 2s |
| NFR-UX-02 | 所有破坏性操作必须二次确认 |
| NFR-UX-03 | 空状态必须有引导（"还没有项目，点击创建"） |
| NFR-UX-04 | 错误提示必须可读，不暴露 stacktrace |

### 4.5 部署

| ID | 需求 |
|---|---|
| NFR-DEP-01 | Docker Compose 单命令起：`docker compose up` |
| NFR-DEP-02 | CI：typecheck + test + lint + build + 镜像 |
| NFR-DEP-03 | 默认 admin/admin123，部署后强制改密 |

---

## 5. 约束与假设

### 5.1 约束

- **数据存储**：SQLite（的同款），内测阶段不切 PG
- **AI 模型**：默认 Claude Opus 4.8；可配置 OpenAI GPT（已有 vendor 实现）
- **License**：保留 VioletEyes 的 `Authorized-Testing-Only`
- **品牌**：紫色系、VE Logo、紫罗兰渐变 + 严重度色条 + Chart.js + Mermaid

### 5.2 假设

- 内测用户上限 200
- 单仓库 ≤ 500MB（zip 解压前）
- 多数仓库 LOC ≤ 500k
- 网络：能访问 OSV.dev（用 VioletEyes 离线缓存兜底）
- LLM Token 价格按 Claude Opus 4.8 输入 $15/M / 输出 $75/M 估算

### 5.3 风险

| 风险 | 等级 | 缓解 |
|---|---|---|
| Skill 上传被用于 prompt injection 攻击 | 高 | NFR-SEC-09/10；签名校验；admin 审核 |
| Smart 模式 LLM 选 skill 不准 | 中 | 记录决策理由 → 用户反馈 → 优化 system prompt |
| SQLite 并发写瓶颈 | 中 | WAL + 限并发 ≤ 3 + 24h scan timeout |
| OSV.dev 不可达 | 低 | 离线缓存（V1.2 已落地） |
| 报告 HTML 离线（无 CDN） | 低 | 全部 inline（VioletEyes 已落地） |

---

## 6. 已知 Bug 修复清单

> 来源：安全规范，下表为**必须修复**的清单（高/中严重度），低优先级项目待 P2。

### 6.1 高危（阻断）

| Bug | 文件:行 | 修复 |
|---|---|---|
| `/api/scan-runs/:id/report` 缺 `JwtAuthGuard` | `apps/api/src/report/report.controller.ts:18-46` | 挂全局 Guard |
| `/api/scan-runs/:id/logs` 缺 Guard | `apps/api/src/scan/scan.controller.ts:34-46` | 装饰器顺序调整 + 挂 Guard |
| Socket.IO `origin:true` + 无 JWT | `apps/api/src/realtime/scan.gateway.ts:26` | origin 白名单 + handleConnection 校验 |
| 前端 token 写 localStorage | `apps/web/src/pages/LoginPage.tsx:45-46` | 内存 + refresh HttpOnly |
| `updatePassword` 不验强度 | `apps/api/src/users/users.service.ts:117-119` | 加 `validatePasswordStrength` |
| 上传 zip 缺 project membership 校验 | `apps/api/src/code-versions/code-versions.controller.ts:62-110` | 加 ProjectRolesGuard |
| zip-bomb 防护缺失 | `apps/api/src/code-versions/code-versions.service.ts:73-83` | 加解压比/文件数/单文件大小限制 |
| `/auth/login` 不支持 email | `apps/api/src/auth/auth.service.ts:121` | `or(eq(username), eq(email))` |
| 默认密钥无校验 | `apps/api/.env.example:18-19` + `docker-compose.yml:65-66` | 启动时校验熵 |
| Docker 镜像 native build `||true` | `apps/api/Dockerfile:40-52` | 移除 `||true` |
| `sub-repo` 不存在时启动 crash | `docker-compose.yml:63-69` | 改为可选挂载 + 缺失时降级 |
| 前端 `signOut` 不调后端 logout | `apps/web/src/hooks/useAuth.ts:84-86` | 调 `/api/auth/logout` 吊销 refresh |
| WebSocket 直连后端 | `apps/web/src/hooks/useScanSocket.ts:40` | 经 nginx 转发 |

### 6.2 中危（计划内修复）

| Bug | 文件:行 | 修复 |
|---|---|---|
| `JWT expiresIn` 8h 与 service 15min 不一致 | `apps/api/src/auth/auth.module.ts:31-34` | 统一 15min |
| `safeExtractZip` 异常路径 tempzip 泄漏 | `apps/api/src/code-versions/code-versions.service.ts:431-520` | 用 try/finally |
| `vuln-library.syncFromVulnerability` 状态错 | `apps/api/src/vulns/vuln-library.service.ts:166-188` | 用传入的 `_newStatus` |
| `updateCoverage` MVP fallback 永远 100% | `apps/api/src/scan/scan-runner.service.ts:559-566` | 删 fallback 或按真实比例 |
| `LIKE` 通配符注入 | `apps/api/src/projects/projects.service.ts:81-91` | 参数化绑定 |
| `randomHex` 用 `Math.random` | `apps/api/src/code-versions/code-versions.service.ts:399-406` | `crypto.randomBytes` |
| `scanLogs` Map 异常路径泄漏 | `apps/api/src/scan/scan-runner.service.ts:571-573` | finally 清理 |
| `coverage.util.ts` filePath 当 route | `apps/api/src/scan/coverage.util.ts:152-155` | 拆分 file-coverage vs route-coverage |
| `parseSourceRef` 切错 fragment | `apps/api/src/git-clone/git-clone.service.ts:217` | 用 URL parser |
| `injectHttpsToken` URL encoding | `apps/api/src/git-clone/git-clone.service.ts:127-139` | encodeURIComponent |
| `vulns.controller.getTrend` 全表扫 | `apps/api/src/vulns/vuln-library.service.ts:106-110` | 加 where + limit |
| `loadAgentInstructions` 无大小限制 | `apps/api/src/agents/loader.ts:36-58` | 加 NFR-SEC-09 |
| `timingSafeEqual` length-mismatch | `apps/api/src/admin/queue-board/queue-board-auth.middleware.ts:119-132` | 用 `crypto.timingSafeEqual` |
| `SettingsPage` 改密后不清 token | `apps/web/src/pages/SettingsPage.tsx:64-66` | 调 `/api/auth/logout` + 跳登录 |
| 前端 `AppLayout` admin 路由无 guard | `apps/web/src/App.tsx:42-77` | 加 `<RequireAdmin>` |
| `ConfigPage` socks vs socks5 | `apps/web/src/pages/admin/ConfigPage.tsx:1011` | 统一 `socks5` |
| `ProjectDetailPage` Compare 错误共享 state | `apps/web/src/pages/ProjectDetailPage.tsx:451-660` | 局部 error state |
| 扫描轮询 + WebSocket 不去重 | `apps/web/src/pages/ScanPage.tsx:50-58` | WebSocket 收 status 后取消轮询 |

### 6.3 视觉重构（VioletEyes 风格）

| 组件 | 现风格 | 目标 |
|---|---|---|
| 主色 | shadcn slate | `#7c3aed` 紫罗兰 |
| Logo | 纯文字 | 渐变方块 `from-violet-500 to-violet-700` + "VE" |
| Severity bar | 无 | 左侧 4px 色条（Critical `#dc2626` ...） |
| Cover | 无 | 紫光径向渐变 + 网格纹理 + 毛玻璃徽章 |
| Header | 白底 | `backdrop-blur bg-white/80` |
| 图表 | 无 | Chart.js 环形图 + 水平柱状图 |
| 调用链 | 文本 | 树形文本 + Mermaid 双 Tab |
| 字体 | Inter | JetBrains Mono（代码）/ Inter（正文） |

---

## 7. 验收标准（Definition of Done）

| 阶段 | 验收 |
|---|---|
| Phase 1 | 登录/项目/代码版本/auth CRUD 通过测试；所有高危 bug 修复完成 |
| Phase 2 | Skill 上传/启用/停用/执行通过测试；admin 审核流程跑通 |
| Phase 3 | 4 种扫描模式在 3 个样例仓库上跑通端到端 |
| Phase 4 | HTML 报告复用 VioletEyes 模板渲染成功，视觉与原版一致 |
| Phase 5 | UI 视觉重构完成；WCAG AA 通过 |
| Phase 6 | Docker Compose `up` 一键启动；CI 绿；文档齐 |

---

## 8. 成功指标（业务可行性）

| 指标 | 目标（内测 3 个月） |
|---|---|
| 注册用户 | ≥ 50 |
| 完成扫描次数 | ≥ 200 |
| 平均 Smart 模式耗时 | ≤ 20 分钟 |
| Smart 模式 skill 选择准确率（人工抽样 50 次） | ≥ 70% |
| HTML 报告打开率 | ≥ 80% |
| Skill 上传次数 | ≥ 10 个社区贡献 |
| 用户 7 日留存 | ≥ 30% |

---

## 9. 已决策问题（2026-06-30 拍板）

| # | 问题 | 决策 |
|---|---|---|
| 1 | Smart 模式是否允许 LLM 拒绝/添加 skill？ | **不允许用户勾选**——Smart 模式由 LLM 自主从 `project.enabledSkills` 中挑选；violeteyes-full 强制加载 |
| 2 | 是否提供"试用"skill 模式？ | **不提供**——MVP 范围收敛 |
| 3 | 第三方 skill 安全审核流程？ | **选项 C：自动 lint + 沙箱跑一遍**——admin 抽查为辅 |
| 4 | 报告是否显示 token 成本？ | **显示**——增强用户信任 + 自检成本 |
| 5 | 差异扫描（增量） | P2（暂不做） |
| 6 | 定时扫描 | P2（暂不做） |

---

## 10. 文档索引

- 详细技术规格 → [02-specification.md](./02-specification.md)
- 开发计划 → [03-development-plan.md](./03-development-plan.md)
- VioletEyes 原版 skill 文档 → `../../SKILL.md`
- VioletEyes 视觉规范 → `../05-html-report.md`