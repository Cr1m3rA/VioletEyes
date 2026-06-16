---
name: VioletEyes
description: 面向白盒源码安全审计的 AI Agent Skill，开发者 Cr1m3rA。覆盖 Java / Spring / Kotlin / Python / Django / Flask / FastAPI / PHP / Laravel / Node.js / Express / NestJS / Go / Gin / Echo / Ruby / Rails / C# / .NET / Vue / React / Angular 等主流前后端框架以及不完整代码片段。Agent 先识别项目语言与开发框架，根据框架特征定位入口文件 / 主函数 / 路由表，再通过目录结构与文件名做步进式、按需的代码读取（避免一次性拉全仓库），对潜在 sink 点做污染传播分析，输出单文件 HTML 审计报告。V1.2 起集成 OSV.dev 联网 CVE 扫描与离线缓存，自动匹配已知漏洞并升级 Critical/High 为 finding。覆盖 OWASP Top 10、API Security Top 10 与主流语言特有的反序列化 / 注入 / 越权 / 配置类漏洞。无需任何 MCP，纯静态分析 + LLM 推理。当前版本为单体白盒审计 Skill，黑盒联动（与渗透测试方向的配套 Skill）处于待开发状态，仅保留接口字段与抽取脚本。
version: 1.2.0
author: Cr1m3rA
license: Authorized-Testing-Only
tags:
  - security
  - code-audit
  - static-analysis
  - sast
  - whitebox
  - taint-analysis
  - owasp
  - cwe
  - vulnerability-scanning
  - multi-language
  - java
  - python
  - php
  - nodejs
  - go
  - ruby
  - csharp
  - vue
  - react
  - angular
  - snippet-audit
  - dependency-cve
triggers:
  - "代码审计"
  - "code audit"
  - "source code review"
  - "源码审计"
  - "静态分析"
  - "static analysis"
  - "SAST"
  - "白盒"
  - "白盒测试"
  - "whitebox"
  - "代码安全"
  - "代码漏洞"
  - "review code"
  - "审计代码"
  - "审计仓库"
  - "审计项目"
  - "audit repository"
  - "漏洞挖掘"
  - "依赖 CVE"
  - "third-party CVE"
  - "OSV 扫描"
  - "Log4Shell"
  - "Spring4Shell"
mcp_dependencies: []
capability_modes:
  - name: standard
    description: 纯 LLM + 内置脚本的源码审计模式（无 MCP 依赖）
    tools_count: 0
    enables:
      - framework_detection
      - entry_point_discovery
      - incremental_code_reading
      - sink_pattern_matching
      - taint_propagation_llm
      - snippet_mode
      - html_reporting
      - owasp_mapping
      - cwe_mapping
inputs:
  - name: source
    type: string
    description: 待审计的代码源（本地目录路径 / Git URL / 压缩包 / 文本片段）
    required: true
  - name: mode
    type: string
    enum: [full, incremental, snippet, api-focused, frontend-focused, diff]
    default: full
  - name: languages
    type: array
    description: 限定审计语言（不指定则按检测结果自动选择）
    default: []
  - name: scope
    type: array
    description: 限定审计范围（路径前缀 / 包名 / 目录）
    default: []
  - name: focus
    type: array
    description: 重点关注的漏洞类型（sqli / xss / ssrf / idor / deser / ssti / cmdi ...）
    default: []
  - name: severity_floor
    type: string
    enum: [info, low, medium, high, critical]
    default: low
    description: 报告输出最低严重度
  - name: max_findings
    type: integer
    default: 100
    description: 单次审计最多输出漏洞数（防止 token 爆炸）
  - name: report_path
    type: string
    default: ./code-audit-report.html
  - name: include_snippet
    type: boolean
    default: true
    description: 是否在报告中保留 vulnerable code 片段
  - name: token_budget
    type: integer
    default: 200000
    description: 步进式读取的 token 上限（超过则停止扩张并先出报告）
outputs:
  - name: report
    type: file
    description: HTML 源码审计报告
  - name: findings
    type: array
    description: 结构化漏洞清单（finding-schema.json）
  - name: assets
    type: array
    description: 受审计的代码资产清单（routes / controllers / components / configs）
  - name: framework_profile
    type: object
    description: 识别出的语言 / 框架 / 入口 / 路由表
  - name: execution_log
    type: file
    description: Agent 步进式读取与决策日志
---

# VioletEyes — 源码安全审计 Agent

> 开发者 Cr1m3rA · 仅限已获授权的安全测试与代码评审

## What this Skill does

本 Skill 使 LLM Agent 在**无 MCP 依赖**的前提下，对任意规模的源码仓库（亦支持不完整代码片段）进行白盒安全审计：

1. **语言与框架识别** — 基于文件名、扩展名、关键文件与依赖清单（`pom.xml`、`requirements.txt`、`go.mod`、`composer.json`、`package.json`、`Gemfile`、`*.csproj` 等），输出 `framework_profile`。
2. **入口定位** — 根据框架特征确定主入口（`main` / `app` / `index` / 路由注册文件 / Spring Boot `@SpringBootApplication` / FastAPI `app = FastAPI()` / Express `app.use(...)` / Laravel `routes/web.php` / Rails `routes.rb` / Gin `r.GET(...)` / NestJS `@Controller()` / Vue `createApp` / React `ReactDOM.createRoot`）。
3. **步进式代码读取** — **不一次性读取整个仓库**。Agent 按目录结构、文件名与框架特征构建读队列，按依赖图展开：入口 → 路由 → 控制器 → 服务 → 仓储 → 模型 → 工具类。每个文件读完后立即评估 sink / source，再决定是否展开调用方。
4. **漏洞挖掘** — 对每个文件依次执行：sink 模式匹配（SQL 拼接、`eval`、`exec`、`Runtime.exec`、`deserialize`、`render_template`、`fs.readFile`、JS `innerHTML`、`v-html`、`dangerouslySetInnerHTML`、Python `pickle.load`、PHP `unserialize`、Java `ObjectInputStream`、Go `exec.Command` …）→ 反向追溯 source（用户输入 / 配置 / HTTP body / 路由参数）→ LLM 语义判断可达性、净化措施、影响面 → 给出 confidence。
5. **片段模式 (snippet mode)** — 当 `source` 是文本片段时，跳过文件树构建，直接对片段做语言检测与 sink/source 推理。
6. **HTML 报告** — 单文件 HTML，**完全离线**（Tailwind v4 / Alpine.js / Chart.js / Mermaid.js / Prism.js 全部内联），输出至 `report_path`。详见 `docs/05-html-report.md` 与 `templates/`。

## When to use

- 用户给出**本地仓库 / Git URL / 压缩包**，要求做安全审计、Code Review、漏洞挖掘。
- 用户贴出**一段代码片段**（一个函数、一个 controller、一个组件）询问其中是否存在漏洞。
- 用户的 PR 引入了新接口、新反序列化点、新文件操作或新 ORM 调用，需要快速做 SAST。
- 用户询问“这个 Spring Boot 项目 / 这个 Express 接口 / 这个 Vue 组件 / 这个 Python 脚本是否安全”。

## When NOT to use

- 用户未提供代码或仓库，且未授权扫描第三方系统 → **拒绝**。
- 用户的真实需求是“运行起来看看” → 改用 `run` / `verify` skill。
- 目标是纯二进制、固件或移动 App 字节码 → 不适用。
- 用户要求“自动修复漏洞并提交 PR” → 不在范围内（仅产出修复建议）。
- 仓库体积过大（>5GB）或仅含 lock 依赖而无源码 → 仅做 manifest / 顶层结构级粗扫。

## Operating principles

1. **步进优先** — 任何时候都先 `ls / tree` + 读 manifest，再决定读哪些文件。
2. **token 节流** — 一次 `Read` 控制在 1500 行以内；超过则用 `offset / limit` 分块；同一文件不重复读取。
3. **证据可定位** — 每条 finding 必须给出 `file:line` + vulnerable code 片段 + 触发路径。
4. **可复现** — 报告中给出可被另一名工程师独立验证的 PoC（HTTP 请求、输入样本、调用链），但**不直接执行**。
5. **白盒边界** — 不修改用户代码、不执行危险命令；建议的 PoC 仅以 `curl` / 单元测试 / 代码片段形式存在。
6. **LLM 推理 > 模式匹配** — grep 命中的 sink 必须经 LLM 上下文推理（是否真可达？是否有防护？是否在受信上下文？）方可上升为 finding。
7. **报告脱敏** — 代码中的密钥、内部 IP、真实账号仅截取必要最小上下文。

## 关于黑盒联动（待开发）

本 Skill 在 finding 字段中保留了 `url_or_path` / `method` / `parameter` 等结构化字段，
并提供 `scripts/extract_for_blackbox.py` 作为抽取接口，便于将来与渗透测试方向的配套 Skill 联动。

**当前状态：待开发。** 配套黑盒 Skill 尚未实现，本 Skill 不会调用任何外部渗透测试服务。
一旦该 Skill 落地，会在 `README.md` 第八节补全字段映射与调用方式。

## 第三方依赖 CVE 扫描（V1.2 新增）

V1.2 起集成 **OSV.dev**（[osv.dev](https://osv.dev)，免费无鉴权）作为主要漏洞源，
在 Step 3 入口定位之后、Step 4 步进式读取之前插入 **Step 3.5 第三方依赖 CVE 扫描**。

**核心流程**：

1. `framework_detect.py --emit-deps-json` 解析所有 14 类 manifest 抽取 `(ecosystem, package, version)` 三元组
2. `cve_lookup.py` 对每个三元组调 OSV.dev `POST /v1/query`，无网时回落至 `payloads/vulnerable-ranges.json` 离线缓存
3. Critical/High 自动追加为 finding（复用现有 `vuln_class` 枚举：`dangerous-deps` / `log4shell` / `spring4shell`）
4. 输出 `dependency_cve.json`，由 `render_report.py --cve-input` 渲染到报告的「第三方依赖 CVE 在线扫描」section

**何时启用**：

- 用户给出**含 manifest 的仓库**（pom.xml / package.json / requirements.txt / go.mod / Gemfile / composer.json / Cargo.toml / *.csproj / packages.config / build.gradle(.kts)）
- 用户希望看到"已知公开漏洞"快速扫描结果（无需复现 PoC）
- 用户在内网环境运行 → `--offline` 强制走缓存

**何时不启用**：

- 用户输入是单段代码（snippet） → snippet 无 manifest，跳过
- 用户只关心业务逻辑漏洞 → CVE 扫描不在范围内
- 用户要求"自动修复并 PR" → CVE 数据只用于报告，不触发修改

**已知边界**：

- ❌ **lockfile 不解析**（V1.3 计划）—— 可能过度告警
- ❌ **传递依赖不解析**（V1.3 计划）—— 只扫直接依赖
- ⚠️ **CVSS 缺失** —— 回落到 GHSA severity；都没有则标 `Unknown`
- ⚠️ **缓存陈旧 > 90 天** —— Dashboard 软提示，不阻断

详细协议、字段映射、限流策略、缓存格式见 [`docs/07-dependency-cve.md`](docs/07-dependency-cve.md)。

## Directory layout

```
VioletEyes/
├── README.md
├── SKILL.md                  当前文件（Agent 入口）
├── skill.json                元数据 / 输入输出契约
├── system-prompt.md          Agent 推理合同
│
├── docs/
│   ├── 01-architecture.md
│   ├── 02-framework-signatures.md
│   ├── 03-code-reading-strategy.md
│   ├── 04-vulnerability-catalog.md
│   ├── 05-html-report.md
│   └── 06-llm-static-analysis.md
│
├── workflows/
│   ├── full-audit.md
│   ├── incremental-audit.md
│   ├── api-audit.md
│   ├── frontend-audit.md
│   └── snippet-audit.md
│
├── signatures/               框架 / 入口 / sink / source 特征
│   ├── backend-frameworks.md
│   ├── frontend-frameworks.md
│   ├── entry-point-patterns.md
│   ├── dangerous-functions.md
│   └── dangerous-configs.md
│
├── templates/                Jinja2 模板 + 内联资源
│   ├── base.html.j2          主骨架
│   ├── base.css              定制 CSS（print / 卡片 / call-chain 等）
│   ├── finding.html.j2       finding 卡片
│   ├── partials/             cover / dashboard / framework / appendix ...
│   │   ├── cover.html.j2
│   │   ├── summary.html.j2
│   │   ├── dashboard.html.j2
│   │   ├── framework.html.j2
│   │   ├── findings_index.html.j2
│   │   ├── appendix.html.j2
│   │   └── disclaimer.html.j2
│   ├── inline/               第三方 JS/CSS 内联（build_inline.py 下载）
│   ├── archive/              历史模板归档
│   ├── finding-schema.json
│   └── asset-schema.json
│
├── scripts/                  静态分析辅助脚本（Python）
│   ├── render_report.py      Jinja2 渲染器（兼容 v1.0 CLI）
│   ├── build_inline.py       下载 / 刷新 inline 资源
│   ├── framework_detect.py
│   ├── sink_detect.py
│   ├── tree_index.py
│   └── extract_for_blackbox.py    （黑盒联动接口，待开发）
│
├── tests/                    冒烟测试 + fixture
│   ├── smoke_test.py         27 项断言
│   ├── preview_server.py     本地预览 HTTP
│   └── fixtures/             findings.json / assets.json / profile.json / execution.log
│                              + code-audit-report.html（示例输出）
│
├── examples/
│   ├── spring-boot-audit.md
│   ├── express-audit.md
│   └── vue-react-audit.md
│
├── payloads/
│   ├── sink-patterns.md
│   ├── taint-sources.md
│   └── dangerous-defaults.md
│
└── .claude/
    └── settings.json
```
