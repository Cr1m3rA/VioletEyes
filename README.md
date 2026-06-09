# VioletEyes

> 面向白盒源码审计的 AI Agent Skill。  
> 兼容 Claude Code / Cline / Roo Code / Cursor / Continue 等 Agent 框架。  
> 无需任何 MCP，文件系统 + LLM 推理即可工作。

- **Skill 名称**：`VioletEyes`
- **版本**：1.0.0
- **协议**：仅限已获授权的安全测试、代码评审与安全研究
- **Agent 入口**：`SKILL.md`
- **元数据**：`skill.json`

[![OWASP](https://img.shields.io/badge/OWASP-Top%2010%20%2B%20API%20Top%2010-3F5E96)](docs/04-vulnerability-catalog.md) [![CWE](https://img.shields.io/badge/CWE-Mapped-orange)](docs/04-vulnerability-catalog.md) [![CVSS](https://img.shields.io/badge/CVSS-v3.1%20Inspired-red)](docs/05-html-report.md) [![Multi--Lang](https://img.shields.io/badge/Multi--Language-10%2B%20Languages-blue)](#二支持的语言与框架) [![Snippet](https://img.shields.io/badge/Snippet--Mode-Supported-green)](workflows/snippet-audit.md) [![No%20MCP](https://img.shields.io/badge/MCP-Not%20Required-lightgrey)](#一violeteyes-是什么)

---

## 🛰 一、VioletEyes 是什么

VioletEyes 提供给 LLM Agent 一套**可复用的源码审计工作流**。
当用户给出一个本地仓库、Git URL、压缩包，或一段不完整的代码片段时，
Agent 能够自主完成以下步骤并产出审计报告：

1. 通过 manifest、目录结构、关键文件，识别项目的语言、构建工具与开发框架。
2. 按框架特征定位主入口与全部 HTTP 入口（Controller、Router、Handler、Vue/React 路由）。
3. 采用**步进式读取**策略——按调用图按需展开文件，不一次性拉全仓库，控制 token 消耗。
4. 对每个已读文件做 sink 模式匹配与污染源反向追溯，再交由 LLM 推理可达性、净化措施与影响面。
5. 渲染单文件 HTML 报告，并同时输出 `findings.json` / `assets.json` / `framework_profile.json` / `execution.log` 等结构化产物。

整个过程不发起任何网络请求、不执行真实 PoC、不修改用户代码，
所有判断都建立在静态阅读与 LLM 语义推理之上。

---

## 🧭 二、支持的语言与框架

**语言层面**：

| 后端 | JVM | 脚本 | 前端 | 配置 / 数据 |
|---|---|---|---|---|
| Java | Kotlin | JavaScript | Vue | SQL |
| C# | Scala | TypeScript | React | YAML |
| Go | Groovy | Python | Angular | JSON |
| Ruby | — | PHP | Svelte | TOML / INI |
| Rust | — | — | — | — |

**框架识别能力（节选）**：

- Java：Spring Boot / Spring MVC / Spring WebFlux、Quarkus、Micronaut、MyBatis、Dubbo、Struts2
- Python：Django / Flask / FastAPI / Tornado / Sanic / aiohttp
- PHP：Laravel / Symfony / ThinkPHP / Yii / CodeIgniter / WordPress
- Node.js：Express / Koa / Fastify / NestJS / Egg / Sails
- Go：Gin / Echo / Fiber / Beego / Iris / Chi
- Ruby：Rails / Sinatra / Hanami
- C#：ASP.NET MVC / ASP.NET Core / Web API
- 前端：Vue 2/3、Nuxt、React、Next、Gatsby、Angular、SvelteKit、Electron、Tauri

完整的入口与特征库见 [`signatures/`](signatures/)。

---

## 🛡 三、漏洞类型与规范遵循

漏洞分类严格对齐 **OWASP Top 10 (2021 / 2025 draft)**、**OWASP API Security Top 10 (2023)** 与 **CWE** 编号体系。
风险评级借鉴 **CVSS v3.1** 的三轴思想（Exploitability / Impact / Confidence），
避免单一分数掩盖实际可利用性差异。

覆盖的典型漏洞类别包括（但不限于）：

- 🧨 **注入类**：SQL 注入、NoSQL 注入、LDAP/XPath 注入、OS 命令注入、`eval` 代码注入、模板注入（SSTI / OGNL / SpEL）
- 🪓 **跨站类**：反射型 / 存储型 / DOM 型 XSS、`v-html` / `dangerouslySetInnerHTML` 误用
- 📁 **文件类**：任意文件读写、路径遍历、Zip Slip、不安全上传
- 💣 **反序列化类**：Java `ObjectInputStream`、PHP `unserialize`、Python `pickle`、Node `node-serialize`、Go `gob`、Ruby `YAML.load`
- 🌐 **网络类**：SSRF、开放重定向、CSRF、CORS 误配置、CRLF 头注入
- 🔐 **鉴权类**：IDOR / BOLA、BFLA、缺失鉴权、JWT 漏洞、Session Fixation
- ⚙️ **配置类**：危险依赖（Log4Shell / Spring4Shell）、默认凭据、Debug 模式开启、缺失安全头、硬编码密钥

详细列表与判定规则见 [`docs/04-vulnerability-catalog.md`](docs/04-vulnerability-catalog.md)。

---

## 🪜 四、五阶段工作方法

| 阶段 | 名称 | 关键动作 |
|---|---|---|
| Phase 1 | 🔍 侦察 (Recon) | 列出顶层目录，读取所有 manifest，输出 `framework_profile.json` |
| Phase 2 | 🧷 入口定位 (Entry Discovery) | 按特征库定位主入口，枚举所有 HTTP 入口，输出 `assets.json` 草稿 |
| Phase 3 | 📖 步进式读取 (Step-wise Reading) | 维护读队列，按 offset/limit 分块读文件，命中 token 预算 80% 即停止 |
| Phase 4 | 🪤 漏洞挖掘 (Mining) | sink 模式匹配 + 反向追溯 + LLM 可达性推理，输出 `findings.json` |
| Phase 5 | 🖨 报告 (Reporting) | 渲染 `templates/report.html` → 写入 `<source>/code-audit-report.html` |

阶段三与阶段四的细节是本 Skill 与“普通读代码”最大的区别，
详见 [`docs/03-code-reading-strategy.md`](docs/03-code-reading-strategy.md) 与
[`docs/06-llm-static-analysis.md`](docs/06-llm-static-analysis.md)。

---

## 🚀 五、使用方法

### 5.1 加载 Skill

**Claude Code**：

```bash
claude --add-dir ~/.claude/skills/VioletEyes
```

**Cline / Roo Code**：

将 `VioletEyes/` 目录复制到 `<workspace>/.claude/skills/`，框架会自动发现 `SKILL.md`。

### 5.2 选定工作流

`SKILL.md` 内部会根据用户输入自动选择合适的工作流，亦可显式指定：

| 工作流 | 适用场景 |
|---|---|
| `full-audit` | 默认。从 manifest 推断到出报告，跑完五阶段 |
| `snippet-audit` | 输入是单段代码，无目录结构时使用 |
| `api-audit` | 只审 HTTP 入口（controller / router / handler） |
| `frontend-audit` | 只审 Vue / React / Angular 与前端存储 |
| `incremental-audit` | 只审 diff，做 PR 级别的快速扫描 |

完整定义见 [`workflows/`](workflows/)。

### 5.3 提交审计目标

支持的输入形式包括：

- 本地目录：`请审计 /path/to/repo`
- Git URL：`请审计 https://github.com/xxx/yyy`（Agent 会自动 clone 到临时目录）
- 压缩包：`请审计 ~/Downloads/app.zip`（Agent 会解压）
- 代码片段：直接粘贴到对话中并说明“审计这段代码”

### 5.4 阅读报告

报告默认输出到 `<source>/code-audit-report.html`，单文件，可直接交付或归档。
同一目录下还会生成 `findings.json`（结构化漏洞清单）、`assets.json`（受审计代码资产清单）、
`framework_profile.json`（识别出的语言/框架/入口画像）以及 `execution.log`（Agent 步进决策日志）。

报告视觉规范、HTML 模板与渲染脚本见 [`docs/05-html-report.md`](docs/05-html-report.md) 与
[`templates/`](templates/)。

---

## 🚧 六、能力边界

**允许的行为**：

- 静态读取代码与 LLM 推理。
- 渲染 HTML 报告与结构化 JSON。
- 给出可被另一名工程师独立验证的 PoC 文本（curl 命令、单元测试片段、调用链示例）。

**禁止的行为**：

- 修改用户代码、提交 PR、向目标仓库写入任何内容。
- 执行真实 PoC 攻击、发起网络请求、向第三方系统写入。
- 替人工复核所有 Critical / High 风险——本 Skill 仅产出候选与建议，最终确认权仍在工程师。

**授权要求**：

- 输入来源必须为用户自有代码、已获授权的目标，或公开 CVE 复现仓库。
- 未授权扫描第三方系统所产生的一切后果，由使用者自行承担。

---

## 🗂 七、目录结构

```
VioletEyes/
├── README.md
├── SKILL.md                  Agent 入口
├── skill.json                元数据 / 输入输出契约
├── system-prompt.md          Agent 推理合同
│
├── docs/                     详细设计
│   ├── 01-architecture.md
│   ├── 02-framework-signatures.md
│   ├── 03-code-reading-strategy.md
│   ├── 04-vulnerability-catalog.md
│   ├── 05-html-report.md
│   └── 06-llm-static-analysis.md
│
├── workflows/                工作流定义
│   ├── full-audit.md
│   ├── incremental-audit.md
│   ├── api-audit.md
│   ├── frontend-audit.md
│   └── snippet-audit.md
│
├── signatures/               框架 / 入口 / sink 特征库
│   ├── backend-frameworks.md
│   ├── frontend-frameworks.md
│   ├── entry-point-patterns.md
│   ├── dangerous-functions.md
│   └── dangerous-configs.md
│
├── templates/                报告 / 数据模板
│   ├── report.html
│   ├── finding-schema.json
│   └── asset-schema.json
│
├── scripts/                  辅助脚本（Python）
│   ├── render_report.py
│   ├── framework_detect.py
│   ├── sink_detect.py
│   ├── tree_index.py
│   └── extract_for_blackbox.py   （预留接口，见第八节）
│
├── examples/                 典型审计样例
│   ├── spring-boot-audit.md
│   ├── express-audit.md
│   └── vue-react-audit.md
│
├── payloads/                 sink 模式 / 污染源 / 危险默认配置
│   ├── sink-patterns.md
│   ├── taint-sources.md
│   └── dangerous-defaults.md
│
└── .claude/
    └── settings.json
```

---

## 🔌 八、配套 Skill：黑盒联动（待开发）

> **状态：待开发。** 本节为占位说明，配套的黑盒方向 Skill 当前**尚未实现**，
> 计划中而非已发布。代码中保留了联动所需的字段定义（`url_or_path` / `method` / `parameter`）与
> 一个抽取脚本（`scripts/extract_for_blackbox.py`），仅作接口预留，**目前不会调用任何外部服务**。

后续落地时，将由 VioletEyes 产出的 `findings.json` 抽出可疑目标清单，
交由配套的渗透测试 Skill 做黑盒 PoC 验证，最终形成“白盒定位 + 黑盒验证”的双报告闭环。
具体字段映射、调用方式与合并归档方案将在该 Skill 发布后于本节补全。

---

## 🧪 九、样例

完整审计演示见 [`examples/`](examples/)：

- [`spring-boot-audit.md`](examples/spring-boot-audit.md) — Spring Boot + MyBatis 全量审计
- [`express-audit.md`](examples/express-audit.md) — Express + MongoDB 原型链污染审计
- [`vue-react-audit.md`](examples/vue-react-audit.md) — Vue `v-html` / React `dangerouslySetInnerHTML` 审计

---

## 📝 十、备注

- 本工具的“智能”来自 LLM 对调用链与上下文的推理；grep / Read 仅负责把相关代码搬入上下文，
  **判断 sink 是否真实可达永远是 LLM 的事**。
- 在生产环境使用前，请人工复核所有 Critical / High 风险。
- 反馈与改进建议可通过仓库 Issue 提交。
