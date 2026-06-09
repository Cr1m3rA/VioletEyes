# CodeAuditSkill — AI Agent 驱动的多语言源码安全审计 Skill

> 一个面向**白盒 / 灰盒源码审计**的 AI Agent Skill。  
> 兼容 Claude Code / Cline / Roo Code / Cursor / Continue 等 Agent 框架。  
> 报告视觉与 [`pentestskill`](../pentestskill) 完全一致——同一团队、同一审稿人，可以把"白盒 + 黑盒"两份报告并排归档。

[![OWASP](https://img.shields.io/badge/OWASP-Top%2010%20%2B%20API%20Top%2010-3F5E96)]() [![CWE](https://img.shields.io/badge/CWE-Mapped-orange)]() [![Multi--Lang](https://img.shields.io/badge/Multi--Language-Java%20%2F%20Python%20%2F%20PHP%20%2F%20Node%20%2F%20Go%20%2F%20Ruby%20%2F%20.NET%20%2F%20Vue%20%2F%20React-blue)]() [![Snippet](https://img.shields.io/badge/Snippet--Mode-Supported-green)]()

---

## ✨ 核心特性

| 维度 | 能力 |
| --- | --- |
| 🔍 **多语言** | Java / Kotlin / Python / PHP / JavaScript / TypeScript / Go / Ruby / C# / Rust + Vue / React / Angular / Svelte 模板 + SQL / YAML / JSON / TOML / INI |
| 🧭 **框架识别** | 基于 manifest + 目录结构 + 关键文件，自动推断语言 / 框架 / 入口 / 路由表 |
| 📖 **步进式读取** | **不一次性拉全仓库**——按入口 → 路由 → 控制器 → 服务 → 仓储的依赖图，按需 Read 关键文件，token 预算可控 |
| 🧠 **LLM 静态分析** | sink 模式匹配后由 LLM 推理可达性、净化、上下文（不是 grep 一票否决） |
| 🧩 **片段模式** | 输入是单段代码时也能审计（语言检测 + sink 推理） |
| 📦 **增量审计** | 支持只审计 diff 变更部分（增量 / PR review 场景） |
| 🪜 **依赖风险** | 读 manifest 联动检测 Log4Shell / Spring4Shell / 已知高危 CVE 依赖 |
| 📊 **专业报告** | 单文件 HTML，视觉与 pentestskill 对齐：风险分布、漏洞详情、PoC、修复建议、调用链 |
| ⚖️ **风险评级** | CVSS v3.1 思想 + Exploitability / Impact / Confidence 三维度 |
| 🤝 **白盒 + 黑盒** | finding 中带 `url / method / parameter`，与 `pentestskill` 黑盒报告交叉对照 |

---

## 🆚 与 pentestskill 的定位差异

| 维度 | pentestskill（黑盒） | code-audit-skill（白盒） |
|---|---|---|
| 输入 | 目标 URL / Burp 流量 | 仓库 / 代码片段 |
| 工具链 | Burp Suite MCP | 文件系统 + LLM（无需 MCP） |
| 主要证据 | HTTP 请求/响应 | 代码片段 + 调用链 |
| 擅长 | 验证漏洞可利用性 | 定位漏洞根因 |
| 报告 | `pentest-report.html` | `code-audit-report.html`（**视觉一致**） |

> **协同用法**：跑 `code-audit-skill` 拿到根因与修复建议 → 跑 `pentestskill` 对报告中 `parameter / url / endpoint` 做黑盒 PoC 验证 → 两份报告并排交付。

---

## 📁 目录结构

```
code-audit-skill/
├── README.md
├── SKILL.md                     ← Agent 入口
├── skill.json                   ← 元数据
├── system-prompt.md             ← Agent 推理合同
│
├── docs/                        ← 详细设计
│   ├── 01-architecture.md
│   ├── 02-framework-signatures.md
│   ├── 03-code-reading-strategy.md
│   ├── 04-vulnerability-catalog.md
│   ├── 05-html-report.md
│   └── 06-llm-static-analysis.md
│
├── workflows/                   ← 工作流
│   ├── full-audit.md
│   ├── incremental-audit.md
│   ├── api-audit.md
│   ├── frontend-audit.md
│   └── snippet-audit.md
│
├── signatures/                  ← 框架/入口/sink 特征库
│   ├── backend-frameworks.md
│   ├── frontend-frameworks.md
│   ├── entry-point-patterns.md
│   ├── dangerous-functions.md
│   └── dangerous-configs.md
│
├── templates/                   ← 报告 / 数据模板
│   ├── report.html              ← 视觉与 pentestskill 一致
│   ├── finding-schema.json
│   └── asset-schema.json
│
├── scripts/                     ← 辅助脚本（Python）
│   ├── render_report.py
│   ├── framework_detect.py
│   ├── sink_detect.py
│   └── tree_index.py
│
├── examples/                    ← 典型审计场景
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

---

## 🚀 快速开始

### 1. 加载 Skill

**Claude Code**：
```bash
claude --add-dir ~/.claude/skills/code-audit-skill
```

**Cline / Roo Code**：
把 `code-audit-skill/` 复制到 `<workspace>/.claude/skills/`，框架自动发现 `SKILL.md`。

### 2. 输入审计目标

支持 4 种形式：

| 形式 | 说明 |
|---|---|
| 本地目录 | `请审计 /path/to/repo` |
| Git URL | `请审计 https://github.com/xxx/yyy`（Agent 会自动 clone 到临时目录） |
| 压缩包 | `请审计 ~/Downloads/app.zip`（Agent 会解压） |
| 代码片段 | 把代码贴到对话里并说"审计这段代码" |

### 3. 选工作流

- **完整审计**（默认）：从 manifest 推断 → 步进读 → 出报告
- **片段审计**：直接对代码片段做语言检测 + sink 推理
- **API 专项**：只盯 controller / router / handler
- **前端专项**：只盯 Vue/React/Angular/模板
- **增量审计**：只审计 diff

### 4. 阅读报告

报告输出到 `<source>/code-audit-report.html`（默认），单文件，可直接交付或归档。

---

## 📚 适用场景

| 场景 | 适用度 | 说明 |
| --- | --- | --- |
| Java Spring Boot 全量审计 | ⭐⭐⭐⭐⭐ | manifest → Application → Controller → Service → Repository 步进读 |
| Python Django / Flask / FastAPI 审计 | ⭐⭐⭐⭐⭐ | urls → views → models → settings |
| PHP Laravel / ThinkPHP 审计 | ⭐⭐⭐⭐⭐ | 路由 + 控制器 + ORM + 模板引擎 SSTI |
| Node.js Express / NestJS 审计 | ⭐⭐⭐⭐⭐ | 路由 + 中间件 + prototype pollution |
| Go Gin / Echo 审计 | ⭐⭐⭐⭐ | main → router → handler |
| Ruby on Rails 审计 | ⭐⭐⭐⭐ | routes → controllers → strong params |
| C# / .NET 审计 | ⭐⭐⭐⭐ | Web API / MVC / Razor |
| Vue / React / Angular 审计 | ⭐⭐⭐⭐ | XSS / v-html / dangerouslySetInnerHTML / 不安全 store |
| 代码片段审计 | ⭐⭐⭐⭐ | 贴一段代码也能出报告 |
| 第三方依赖审计 | ⭐⭐⭐⭐ | manifest → CVE 库联动（Log4Shell / Spring4Shell 等） |
| 业务逻辑漏洞 | ⭐⭐⭐ | 需 LLM 深入推理；本 Skill 仅给出"启发式候选"，建议结合人工 |

---

## 🛡️ 安全 & 合规

- ❌ **禁止**：修改用户代码、提交 PR、执行真实 PoC 攻击
- ✅ **允许**：静态读取 + LLM 推理 + 输出报告 + 给出可粘贴的 PoC 文本
- ✅ **审计**：所有 Read/Bash 调用都在 Agent 执行日志中可见
- ✅ **授权**：本 Skill **不替代授权测试**；使用前请确认输入来源合法

---

## 📜 规范遵循

- **OWASP Top 10 (2021 / 2025 draft)** — 漏洞分类
- **OWASP API Security Top 10 (2023)** — API 专项
- **CWE** — 缺陷分类
- **CVSS v3.1** — 风险评级
- **NIST SP 800-53** — 安全控制参考

详见 [docs/04-vulnerability-catalog.md](docs/04-vulnerability-catalog.md)

---

## 🧪 样例

参见 [examples/](examples/)：

- [spring-boot-audit.md](examples/spring-boot-audit.md) — Spring Boot + MyBatis 完整审计演示
- [express-audit.md](examples/express-audit.md) — Express + MongoDB prototype pollution 审计
- [vue-react-audit.md](examples/vue-react-audit.md) — Vue v-html / React dangerouslySetInnerHTML 审计

---

## 📝 许可证

本 Skill 仅供**已获授权**的安全测试、代码评审、安全研究使用。  
未授权使用本 Skill 对第三方系统进行审计由使用者自行承担法律责任。

---

> 维护者提示：本 Skill 的"智能"来自 LLM 对**调用链**与**上下文**的推理。  
> Grep / Read 只负责把"相关代码"搬进来——**判断 sink 是否真实可达**永远是 LLM 的事。  
> 在生产环境使用前，请**人工复核**所有 Critical / High 风险漏洞。
