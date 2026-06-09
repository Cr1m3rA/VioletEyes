---
name: code-audit-skill
description: AI Agent 驱动的源码安全审计 Skill，覆盖 Java / Spring / Python / Django / Flask / FastAPI / PHP / Laravel / Node.js / Express / NestJS / Go / Gin / Echo / Ruby / Rails / C# / .NET / Vue / React / Angular 等主流前后端框架以及不完整代码片段。Agent 先识别项目语言与开发框架，根据框架特征定位入口文件 / 主函数 / 路由表，再通过目录结构与文件名做步进式、按需的代码读取（避免一次性拉全仓库），对潜在 sink 点做污染传播分析，输出与 pentestskill 风格一致的 HTML 审计报告。覆盖 OWASP Top 10、API Top 10 与主流语言特有的反序列化 / 注入 / 越权 / 配置类漏洞。无需任何 MCP，纯静态分析 + LLM 推理，可与 pentestskill（黑盒流量层）配合使用形成"白盒 + 黑盒"闭环。
version: 1.0.0
author: code-audit-skill
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
    description: HTML 源码审计报告（视觉风格与 pentestskill 一致）
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

# CodeAuditSkill — 自动化源码安全审计 Agent

## What this Skill does

本 Skill 让 LLM Agent 在**无 MCP 依赖**的前提下，对任意规模的源码仓库（也支持不完整代码片段）进行**白盒安全审计**：

1. **语言与框架识别** — 基于文件名 / 扩展名 / 关键文件 / 依赖清单（pom.xml、requirements.txt、go.mod、composer.json、package.json、Gemfile、*.csproj、package.json + 框架特征），输出 `framework_profile`。
2. **入口定位** — 根据框架特征找到主入口（`main` / `app` / `index` / 路由注册文件 / Controller 扫描基类 / Spring Boot `@SpringBootApplication` / FastAPI `app = FastAPI()` / Express `app.use(...)` / Laravel `routes/web.php` / Rails `routes.rb` / Gin `r.GET(...)` / NestJS `@Controller()` / Vue `createApp` / React `ReactDOM.createRoot`）。
3. **步进式代码读取** — **不一次性读取整个仓库**。Agent 按目录结构 + 文件名 + 框架特征构建一个**待读文件队列**（read queue），按依赖图展开：入口 → 路由 → 控制器 → 服务 → 仓储 → 模型 → 工具类。读取每个文件后立刻评估 sink/source，再决定是否展开其调用方。
4. **漏洞挖掘** — 对每个文件做：sink 模式匹配（SQL 拼接、`eval`、`exec`、`Runtime.exec`、`deserialize`、`render_template`、`fs.readFile`、JS `innerHTML`、`v-html`、`dangerouslySetInnerHTML`、Python `pickle.load`、PHP `unserialize`、Java `ObjectInputStream`、Go `exec.Command`…）→ 反向追溯 source（用户输入 / 配置 / HTTP body / 路由参数）→ LLM 语义判断是否可达 + 是否可利用 → 给出 confidence。
5. **片段模式 (snippet mode)** — 当 `source` 是文本片段时，跳过文件树构建，直接对片段做语言检测 + sink/source 推理。
6. **HTML 报告** — 单文件 HTML，视觉与 `pentestskill` 保持一致（同样的颜色、徽章、卡片、Chart.js + Prism.js），方便"白盒+黑盒"两份报告合并归档。

## When to use

- 用户给出**本地仓库 / Git URL / 压缩包**，要求做安全审计、Code Review、漏洞挖掘
- 用户贴出**一段代码片段**（一个函数 / 一个 controller / 一个组件）问"这里有没有漏洞"
- 用户的 PR 引入新接口、新反序列化点、新文件操作、新 ORM 调用，希望快速做 SAST
- 用户问"这个 Spring Boot 项目 / 这个 Express 接口 / 这个 Vue 组件 / 这个 Python 脚本是否安全"
- 与 `pentestskill` 配合：`pentestskill` 在黑盒层产出 PoC → `code-audit-skill` 在白盒层定位根因

## When NOT to use

- 用户未提供代码或仓库，且未授权扫描第三方系统 → **拒绝**
- 仅需求"运行起来看看" → 改用 `run` / `verify` skill
- 目标是纯二进制 / 固件 / 移动 App 字节码 → 不适用
- 用户要求"自动修复漏洞并提交 PR" → 不在范围内（仅产出修复建议）
- 仓库超大（>5GB）或带 lock 依赖但无源码 → 仅做配置/manifest 级粗扫

## Operating principles

1. **步进优先** — 任何时候都先 `ls / tree` + 读 manifest，再决定读哪些文件
2. **token 节流** — 一次 Read 调用尽量 < 1500 行；超过则用 `offset/limit` 分块；同一文件不重复读取
3. **证据必须可定位** — 每个 finding 给出 `file:line` + vulnerable code 片段 + 触发路径
4. **可复现** — 报告中给出可被另一名工程师独立验证的 PoC（HTTP 请求 / 输入样本 / 触发调用链）
5. **白盒边界** — 不修改用户代码、不执行危险命令；建议的 PoC 用 `cat <<EOF` / 文本片段 / 单元测试片段，不直接运行
6. **LLM 推理 > 模式匹配** — grep 出的 sink 必须经过 LLM 上下文推理（是否真可达？是否有防护？是否在受信任上下文？）才能上升为 finding
7. **报告脱敏** — 代码中如有密钥 / 内部 IP / 真实账号，仅截取必要的最小上下文

## 与 pentestskill 的协同

| 维度 | pentestskill（黑盒） | code-audit-skill（白盒） |
|---|---|---|
| 输入 | 目标 URL / 流量 | 仓库 / 代码片段 |
| 工具 | Burp MCP | 文件系统 + LLM |
| 主要证据 | HTTP 请求/响应 | 代码片段 + 调用链 |
| 擅长 | 验证漏洞可利用性 | 定位漏洞根因 |
| 报告 | pentest-report.html | code-audit-report.html |

**协同用法**：
1. 跑 `code-audit-skill` 产出白盒报告 + 文件位置
2. 跑 `pentestskill` 对报告中 `parameter / url / endpoint` 字段做黑盒验证
3. 两份报告合并归档

## Directory layout

```
code-audit-skill/
├── README.md
├── SKILL.md                      ← 你正在看（Agent 入口）
├── skill.json                    ← 元数据 / 输入输出契约
├── system-prompt.md              ← Agent 推理合同
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
├── signatures/                   ← 框架 / 入口 / sink / source 特征
│   ├── backend-frameworks.md
│   ├── frontend-frameworks.md
│   ├── entry-point-patterns.md
│   ├── dangerous-functions.md
│   └── dangerous-configs.md
│
├── templates/
│   ├── report.html               ← 视觉风格与 pentestskill 对齐
│   ├── finding-schema.json
│   └── asset-schema.json
│
├── scripts/                      ← 静态分析辅助脚本（Python）
│   ├── render_report.py
│   ├── framework_detect.py
│   ├── sink_detect.py
│   └── tree_index.py
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
