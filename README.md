# VioletEyes

> 面向白盒源码审计的 AI Agent Skill。  
> 兼容 Claude Code / Cline / Roo Code / Cursor / Continue / Aider 等 Agent 框架。  
> 无需任何 MCP，文件系统 + LLM 推理即可工作。

- **Skill 名称**：`VioletEyes`
- **版本**：1.2.0
- **协议**：仅限已获授权的安全测试、代码评审与安全研究
- **Agent 入口**：`SKILL.md`
- **元数据**：`skill.json`
- **兄弟项目**：[ShadowFox](https://github.com/) — 黑盒 / 灰盒渗透测试方向的配套 Skill（V1.1 起联动）

[![OWASP](https://img.shields.io/badge/OWASP-Top%2010%20%2B%20API%20Top%2010-3F5E96)](docs/04-vulnerability-catalog.md) [![CWE](https://img.shields.io/badge/CWE-Mapped-orange)](docs/04-vulnerability-catalog.md) [![CVSS](https://img.shields.io/badge/CVSS-v3.1%20Inspired-red)](docs/05-html-report.md) [![Multi--Lang](https://img.shields.io/badge/Multi--Language-10%2B%20Languages-blue)](#二支持的语言与框架) [![Snippet](https://img.shields.io/badge/Snippet--Mode-Supported-green)](workflows/snippet-audit.md) [![No%20MCP](https://img.shields.io/badge/MCP-Not%20Required-lightgrey)](#一violeteyes-是什么) [![Offline%20Report](https://img.shields.io/badge/HTML%20Report-Fully%20Offline-violet)](docs/05-html-report.md) [![OSV%20CVE](https://img.shields.io/badge/OSV.dev%20CVE-Live%20Lookup-blueviolet)](#五phase-35-第三方依赖-cve-扫描-v12-新增)

---

## 🛰 一、VioletEyes 是什么

VioletEyes 提供给 LLM Agent 一套**可复用的源码审计工作流**。
当用户给出一个本地仓库、Git URL、压缩包，或一段不完整的代码片段时，
Agent 能够自主完成以下步骤并产出审计报告：

1. 通过 manifest、目录结构、关键文件，识别项目的语言、构建工具与开发框架。
2. 按框架特征定位主入口与全部 HTTP 入口（Controller、Router、Handler、Vue/React 路由）。
3. 采用**步进式读取**策略——按调用图按需展开文件，不一次性拉全仓库，控制 token 消耗。
4. 对每个已读文件做 sink 模式匹配与污染源反向追溯，再交由 LLM 推理可达性、净化措施与影响面。
5. **（V1.1）渲染单文件 HTML 报告**——基于 Jinja2 模板与全内联前端资源，**完全离线**，可直接在内网 / U 盘环境交付。
6. 同时输出 `findings.json` / `assets.json` / `framework_profile.json` / `execution.log` 等结构化产物。

整个过程不发起任何网络请求、不执行真实 PoC、不修改用户代码，
所有判断都建立在静态阅读与 LLM 语义推理之上。

---

## 🎉 二、V1.1 更新摘要

相比 1.0.0，V1.1 是一个**报告层重构 + 工具链增强**版本，核心变更：

| 模块 | V1.0 | V1.1 |
|---|---|---|
| 报告模板 | `templates/report.html`（手写 HTML + 字符串 `replace`） | `templates/base.html.j2` + `finding.html.j2` + `partials/*.j2`（**Jinja2**） |
| 前端资源 | 部分走 CDN / 外链 | **全部内联** —— Tailwind v4 / Alpine.js / Mermaid.js / Chart.js / Prism.js |
| 离线能力 | 需联网加载 CSS/JS | **完全离线**，单文件 ~3.9 MB，gzip 后约 1 MB |
| 暗色模式 | 不支持 | `<html class="dark">` + Alpine.js 切换按钮，初次加载跟随 `prefers-color-scheme` |
| 调用链可视化 | 纯树形文本 | **树形 + Mermaid `flowchart TD`** 双 Tab，sink 节点红色高亮 |
| 严重度图表 | 静态色块 | **Chart.js** 环形图 + 漏洞类型 Top 10 水平柱状图 |
| 代码高亮 | 自写极简着色 | **Prism.js**，覆盖 Java / Python / JS / Go / PHP / Ruby / C# / SQL / YAML |
| 严重度过滤 | 无 | 顶部 filter-chip 多选（All / Critical / High / Medium / Low / Info） |
| 渲染器 | 单文件 `render_report.py` | `render_report.py`（Jinja2）+ `archive_render_report.py`（v1.0 归档） + `build_inline.py`（资源刷新） |
| 测试覆盖 | 无 | `tests/smoke_test.py`（**27 项断言**）+ `preview_server.py` + fixtures |
| 联动方向 | `extract_for_pentest.py`（占位） | `extract_for_blackbox.py` 已就位，配套 **ShadowFox** 黑盒 Skill 落地中 |

完整变更点见 `git log`（关键 commit：`97be953 Update render script`）。

---

## 🛰 V1.2 更新摘要

相比 1.1.0，V1.2 是一个**第三方依赖 CVE 联网扫描**版本，核心新增：

| 模块 | V1.1 | V1.2 |
|---|---|---|
| 依赖漏洞知识库 | 17 个包 × 21 个 CVE 硬编码（`framework_detect.KNOWN_VULN_DEPS`） | **OSV.dev 联网**（免费、无鉴权）+ 离线缓存 fallback |
| Manifest 覆盖 | 11 类 | **15 类**（新增 `build.gradle` Kotlin DSL / `*.csproj` / `packages.config`） |
| 报告层 | 仅静态 `KNOWN_VULN_DEPS` 命中 | 新增「**第三方依赖 CVE 在线扫描**」section（7 列表：依赖 / 版本 / 严重度 / CVE / 固定版本 / 简介 / 链接） |
| 自动升级为 finding | ❌ | ✅ Critical/High 写入 `findings.json`（`vuln_class=dangerous-deps / log4shell / spring4shell`） |
| NVD 链接 | ❌ | ✅ CVE 徽章 → `https://nvd.nist.gov/vuln/detail/<CVE>` |
| 导航 / Dashboard | 无 | 顶部「依赖 CVE (N)」导航；Dashboard「高危依赖」卡新增「在线 CVE 扫描」副行 |
| 内网 / 离线 | ❌ | ✅ `payloads/vulnerable-ranges.json` 内置 11+ 条种子；`--offline` 强制离线 |
| Smoke test | 29 项 | **38 项**（新增 8 项 CVE 相关断言） |

新增 / 修改文件速查：

```
scripts/cve_lookup.py             新增  离线 + 在线 CVE 查询 CLI
scripts/build_cve_cache.py        新增  维护者专用：联网刷新离线缓存
scripts/ecosystems.py             新增  manifest → OSV ecosystem 映射 + 版本归一化
scripts/manifest_parsers.py       新增  15 类 manifest 解析器（提取三元组）
scripts/framework_detect.py       修改  新增 --emit-deps-json CLI flag + *.csproj/packages.config 检测
scripts/render_report.py          修改  新增 --cve-input CLI flag + flatten_dependency_cve() + Jinja context 变量
payloads/vulnerable-ranges.json   新增  离线种子（11+ 条 advisory，10+ 个包）
payloads/vulnerable-ranges.schema 新增  JSON Schema
templates/dependency_cve.schema   新增  dependency_cve.json 输出 JSON Schema
templates/partials/dependency_cve 新增  报告「第三方依赖 CVE 在线扫描」section 模板
templates/base.html.j2            修改  顶部导航 + mobile nav 加「依赖 CVE (N)」链接；include 新 partial
templates/partials/dashboard.j2   修改  「高危依赖」卡新增「在线 CVE 扫描」副行
skill.json                        修改  permissions.network 加 api.osv.dev；inputs/outputs/capabilities 增量
SKILL.md                          修改  version→1.2.0 + 新触发词（依赖 CVE / OSV 扫描）
workflows/full-audit.md           修改  新增 Step 3.5 + 自检项 + 异常处理 3 行
workflows/snippet-audit.md        修改  加一行「不适用：第三方依赖 CVE 扫描」
workflows/api-audit.md            修改  同上
workflows/frontend-audit.md       修改  同上
tests/smoke_test.py               修改  +8 项 CVE 相关断言
tests/fixtures/dependency_cve.json 新增  smoke test 用 fixture
```

**V1.2 完整变更点**见 `git log`（关键 commit：基础 V1.2 重构）。

---

## 🧭 三、支持的语言与框架

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

## 🛡 四、漏洞类型与规范遵循

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

## 🪜 五、五阶段工作方法

| 阶段 | 名称 | 关键动作 |
|---|---|---|
| Phase 1 | 🔍 侦察 (Recon) | 列出顶层目录，读取所有 manifest，输出 `framework_profile.json` |
| Phase 2 | 🧷 入口定位 (Entry Discovery) | 按特征库定位主入口，枚举所有 HTTP 入口，输出 `assets.json` 草稿 |
| Phase 3 | 📖 步进式读取 (Step-wise Reading) | 维护读队列，按 offset/limit 分块读文件，命中 token 预算 80% 即停止 |
| Phase 4 | 🪤 漏洞挖掘 (Mining) | sink 模式匹配 + 反向追溯 + LLM 可达性推理，输出 `findings.json` |
| Phase 5 | 🖨 报告 (Reporting) | Jinja2 渲染 `templates/base.html.j2` → 写入 `<source>/code-audit-report.html` |

阶段三与阶段四的细节是本 Skill 与“普通读代码”最大的区别，
详见 [`docs/03-code-reading-strategy.md`](docs/03-code-reading-strategy.md) 与
[`docs/06-llm-static-analysis.md`](docs/06-llm-static-analysis.md)。

---

## 🚀 六、使用方法

### 6.1 加载 Skill

**Claude Code**：

```bash
claude --add-dir ~/.claude/skills/VioletEyes
```

**Cline / Roo Code / Cursor**：

将 `VioletEyes/` 目录复制到 `<workspace>/.claude/skills/`，框架会自动发现 `SKILL.md`。

### 6.2 选定工作流

`SKILL.md` 内部会根据用户输入自动选择合适的工作流，亦可显式指定：

| 工作流 | 适用场景 |
|---|---|
| `full-audit` | 默认。从 manifest 推断到出报告，跑完五阶段 |
| `snippet-audit` | 输入是单段代码，无目录结构时使用 |
| `api-audit` | 只审 HTTP 入口（controller / router / handler） |
| `frontend-audit` | 只审 Vue / React / Angular 与前端存储 |
| `incremental-audit` | 只审 diff，做 PR 级别的快速扫描 |

完整定义见 [`workflows/`](workflows/)。

### 6.3 提交审计目标

支持的输入形式包括：

- 本地目录：`请审计 /path/to/repo`
- Git URL：`请审计 https://github.com/xxx/yyy`（Agent 会自动 clone 到临时目录）
- 压缩包：`请审计 ~/Downloads/app.zip`（Agent 会解压）
- 代码片段：直接粘贴到对话中并说明“审计这段代码”

### 6.4 本地渲染报告（V1.1）

如果你拿到了 Agent 产出的 JSON / log，想自己重新出报告：

```bash
python scripts/render_report.py \
    --findings       findings.json \
    --assets         assets.json \
    --profile        framework_profile.json \
    --execution-log  execution.log \
    --project-name   "My App" \
    --target         "D:\repo\myapp" \
    --mode           full \
    --severity-floor low \
    --output         code-audit-report.html
```

**全部 CLI 参数**：`--findings` / `--assets` / `--profile` / `--execution-log` / `--output` /
`--project-name` / `--target` / `--mode` / `--severity-floor` /
`--partial` / `--snippet-mode` / `--test-date-start` / `--test-date-end`。

**刷新前端资源**（如需升级 Tailwind / Mermaid 版本，需联网）：

```bash
python scripts/build_inline.py
```

**冒烟测试**（对 fixtures 跑一遍渲染管线 + 27 项断言）：

```bash
python tests/smoke_test.py
```

**本地预览报告**：

```bash
python tests/preview_server.py
# 浏览器打开 http://127.0.0.1:8000/code-audit-report.html
```

### 6.5 阅读报告

报告默认输出到 `<source>/code-audit-report.html`，**单文件、完全离线**，可直接交付或归档。
同一目录下还会生成：

- `findings.json` —— 结构化漏洞清单（finding-schema.json）
- `assets.json` —— 受审计代码资产清单（asset-schema.json）
- `framework_profile.json` —— 识别出的语言/框架/入口画像
- `execution.log` —— Agent 步进决策日志

报告视觉规范、HTML 模板与渲染脚本见 [`docs/05-html-report.md`](docs/05-html-report.md) 与
[`templates/`](templates/)。

---

## 🛰 五、Phase 3.5: 第三方依赖 CVE 扫描（V1.2 新增）

完整工作流：

```bash
# 1. 解析所有 manifest 中的 (ecosystem, package, version) 三元组
python3 scripts/framework_detect.py <repo_path> \
    --emit-deps-json third_party_deps.json

# 2. 联网优先 / 离线 fallback 跑 CVE 查询
python3 scripts/cve_lookup.py <repo_path> \
    --deps-json third_party_deps.json \
    --cache payloads/vulnerable-ranges.json \
    --output dependency_cve.json \
    --findings findings.json \
    --min-severity High

# 3. 渲染报告时把 dependency_cve.json 喂给渲染器
python3 scripts/render_report.py \
    --findings findings.json \
    --assets assets.json \
    --profile framework_profile.json \
    --execution-log execution.log \
    --cve-input dependency_cve.json \
    --output code-audit-report.html
```

**CLI flags 速查（`cve_lookup.py`）**：

| Flag | 默认 | 说明 |
|---|---|---|
| `--repo <path>` | （与 `--deps-json` 二选一） | 仓库根 |
| `--deps-json <path>` | — | 复用 `framework_detect --emit-deps-json` 输出，跳过重复扫树 |
| `--cache <path>` | `payloads/vulnerable-ranges.json` | 离线缓存 |
| `--output <path>` | `dependency_cve.json` | 输出文件 |
| `--findings <path>` | — | 追加 Critical/High 到 `findings.json`（用现有 finding-schema 形状） |
| `--min-severity` | `High` | finding 升级阈值（Low / Medium / High / Critical） |
| `--online` / `--offline` | auto | 强制联网 / 强制离线 |
| `--refresh-cache` | off | 写回新条目到离线缓存（维护者常用） |
| `--rate <n>` | 4 | 并发 OSV 请求上限（max 10） |
| `--timeout <sec>` | 8 | 单请求超时 |
| `--ecosystem <list>` | — | 逗号分隔过滤（`npm,Maven`） |
| `--dry-run` | — | 只解析不写盘 |

**CLI flags（`render_report.py` 新增）**：

| Flag | 默认 | 说明 |
|---|---|---|
| `--cve-input <path>` | `""`（不渲染 CVE section） | `dependency_cve.json` 路径 |

**离线缓存刷新（维护者）**：

```bash
# 按 scripts/seed_packages.json 的种子批量刷新
python3 scripts/build_cve_cache.py --progress
```

覆盖 36 个高使用率包；可手动编辑 `scripts/seed_packages.json` 增删条目。

**报告里长这样**：
- 顶部导航新增 **依赖 CVE (N)** 链接（仅 N > 0 时显示）
- 「框架画像」之后新增「第三方依赖 CVE 在线扫描」section：7 列表，CVE 徽章点击直达 NVD
- Dashboard「高危依赖」卡新增副行 `在线 CVE 扫描 X 条 advisory · 缓存命中 Y`

**已知边界**（详见 `docs/07-dependency-cve.md`）：
- ❌ **lockfile 不解析**（V1.3）：如果 manifest 写 `log4j 2.14.1` 但 `package-lock.json` 锁 `2.17.1`，会「过度告警」。
- ❌ **传递依赖不解析**（V1.3）：只扫直接依赖。
- ⚠️ **OSV.dev 不返回 numeric CVSS 时**，严重度回落到 GHSA severity；都没有则标 `Unknown` 且不出现在升级 finding 列表里。
- ⚠️ **缓存陈旧**：超过 90 天的缓存 Dashboard 会软提示「缓存可能过期」，但不阻断报告。

---

## 🚧 七、能力边界

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

## 🗂 八、目录结构（V1.1）

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
│   ├── 05-html-report.md     ← V1.1 大幅重写
│   └── 06-llm-static-analysis.md
│
├── workflows/                工作流定义
│   ├── full-audit.md
│   ├── incremental-audit.md
│   ├── api-audit.md
│   ├── frontend-audit.md
│   └── snippet-audit.md
│
├── signatures/               框架 / 入口 / sink / source 特征库
│   ├── backend-frameworks.md
│   ├── frontend-frameworks.md
│   ├── entry-point-patterns.md
│   ├── dangerous-functions.md
│   └── dangerous-configs.md
│
├── templates/                报告模板（Jinja2 + 内联资源）── V1.1 重构
│   ├── base.html.j2          主骨架
│   ├── base.css              定制 CSS（print / 卡片 / call-chain）
│   ├── finding.html.j2       finding 卡片
│   ├── partials/             子模板
│   │   ├── cover.html.j2
│   │   ├── summary.html.j2
│   │   ├── dashboard.html.j2
│   │   ├── framework.html.j2
│   │   ├── findings_index.html.j2
│   │   ├── appendix.html.j2
│   │   └── disclaimer.html.j2
│   ├── inline/               Tailwind v4 / Alpine / Mermaid / Chart / Prism 全量内联
│   ├── archive/              v1.0 模板归档（report.html.v1）
│   ├── finding-schema.json
│   └── asset-schema.json
│
├── scripts/                  辅助脚本（Python）
│   ├── render_report.py          ← V1.1 Jinja2 渲染器（当前）
│   ├── archive_render_report.py  ← V1.0 字符串模板渲染器（归档）
│   ├── build_inline.py           ← V1.1 联网刷新 inline 资源
│   ├── framework_detect.py
│   ├── sink_detect.py
│   ├── tree_index.py
│   ├── extract_for_blackbox.py   ← V1.1 重命名（预留 ShadowFox 联动接口）
│   └── README-archive.md         ← 渲染器迁移说明
│
├── tests/                    冒烟测试与预览 ── V1.1 新增
│   ├── smoke_test.py         27 项断言（端到端渲染）
│   ├── preview_server.py     本地 HTTP 预览
│   ├── check_server.py
│   ├── inspect.py
│   └── fixtures/             findings / assets / profile / log + 示例输出 HTML
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

## 🔌 九、配套 Skill：ShadowFox（V1.1 联动）

> **状态：开发中（V1.1 起接入）。** 配套的 **ShadowFox** 黑盒 / 灰盒渗透测试方向 Skill 正在落地，
> 预计 V1.2 正式发布。本节给出已确定的对接约定，便于上下游对齐。

**ShadowFox 是什么**：

- 面向黑盒 / 灰盒渗透测试的 AI Agent Skill。
- 专为「拿到部分源码却需要以黑盒方式完成渗透」的混合测试场景设计。
- Agent 通过读取代码目录，识别接口定义（路由 / Controller / Router），解析权限控制注解 /
  拦截器 / 过滤器，提取全部可用接口并给出请求 / 响应示例；
  同时抽取配置密钥、测试端点、Swagger / OpenAPI 文档、调试接口、敏感注释等对渗透测试有帮助的元信息。
- 最终输出两份交互式 HTML：
  - **接口文档站** —— 自定义域名 / Cookie / Token / Header，一键复制 cURL / fetch，按方法 / 路径 / 权限过滤
  - **代码信息汇总站** —— 资产清单、鉴权矩阵、敏感信息命中、测试建议
- **严格非漏洞发现 skill** —— 不做污点分析、不扫漏洞，仅做信息收集与文档生成。

**联动数据流**（计划）：

```
┌─────────────────┐  findings.json   ┌─────────────────┐
│   VioletEyes    │ ───────────────► │   ShadowFox     │
│   (白盒审计)    │   (url_or_path / │   (黑盒 / 灰盒) │
│                 │    method /      │                 │
│                 │    parameter)    │                 │
└─────────────────┘                  └─────────────────┘
        │                                      │
        ▼                                      ▼
  code-audit-report.html               pentest-report.html
  (漏洞清单 + 调用链)                  (PoC 验证 + 复现记录)
```

**接口预留**：

- `findings.json` 中已包含 `url_or_path` / `method` / `parameter` 字段定义（见 `templates/finding-schema.json`）。
- `scripts/extract_for_blackbox.py` 提供从 `findings.json` 抽取「可疑目标清单」的 CLI。
- 具体字段映射、调用方式与合并归档方案，将在 ShadowFox 正式发布后于本节补全。

---

## 🧪 十、样例

完整审计演示见 [`examples/`](examples/)：

- [`spring-boot-audit.md`](examples/spring-boot-audit.md) — Spring Boot + MyBatis 全量审计
- [`express-audit.md`](examples/express-audit.md) — Express + MongoDB 原型链污染审计
- [`vue-react-audit.md`](examples/vue-react-audit.md) — Vue `v-html` / React `dangerouslySetInnerHTML` 审计

也可直接打开 [`tests/fixtures/code-audit-report.html`](tests/fixtures/) 查看 V1.1 渲染管线的真实输出样例。

---

## 📝 十一、备注

- 本工具的“智能”来自 LLM 对调用链与上下文的推理；grep / Read 仅负责把相关代码搬入上下文，
  **判断 sink 是否真实可达永远是 LLM 的事**。
- 在生产环境使用前，请人工复核所有 Critical / High 风险。
- 报告中的所有 JS / CSS 已在生成时内联，**不依赖任何 CDN**；如需升级前端库版本，运行 `python scripts/build_inline.py`。
- 反馈与改进建议可通过仓库 Issue 提交。
