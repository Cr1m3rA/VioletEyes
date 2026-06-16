# 05 — HTML 审计报告

> 本节定义 VioletEyes 产出的 `code-audit-report.html` 的结构、视觉规范、占位符与渲染管线。
> **v1.1 更新**：报告从手写 HTML/CSS + 字符串模板拼接，重构为 **Jinja2 模板 + 全内联前端资源**，并在浏览器侧引入 **Tailwind v4 / Alpine.js / Mermaid.js / Chart.js / Prism.js** 提升视觉与交互。

## 5.1 渲染管线（v1.1）

```
┌──────────────────────────────────────────────────────────────────┐
│   Python 端（一次性）                                              │
│                                                                  │
│   findings.json ─┐                                                │
│   assets.json   ─┼─► scripts/render_report.py ──► code-audit-    │
│   profile.json  ─┤                  │                  report.html│
│   execution.log ─┘                  ▼                             │
│                          Jinja2 模板（templates/）                │
│                          ├─ base.html.j2                          │
│                          ├─ finding.html.j2                       │
│                          └─ partials/*.html.j2                    │
│                                                                  │
│   模板内联：templates/inline/*  → 一次性 read_text                │
│           （Tailwind/Alpine/Chart/Mermaid/Prism 全量）            │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│   浏览器端（运行时）                                                │
│                                                                  │
│   Tailwind v4  ─► JIT 编译 utility class（violet/slate/...）       │
│   Alpine.js    ─► 折叠 / 主题切换 / 严重度过滤 / call-chain tab   │
│   Chart.js     ─► 严重度环形图 + 漏洞类型水平柱状图                │
│   Mermaid.js   ─► 调用链流程图（flowchart TD）                    │
│   Prism.js     ─► 代码块语法高亮（Java/Python/JS/Go/PHP/Ruby/...）│
└──────────────────────────────────────────────────────────────────┘
```

**单文件交付**：所有上述 JS/CSS 在生成时已 inline 进 HTML。报告不依赖任何 CDN 或外部资源，离线 / 内网环境直接打开。

**离线资源刷新**：如需升级 Tailwind / Mermaid 等版本，运行 `python scripts/build_inline.py`（一次性联网）。

## 5.2 视觉规范

| 维度 | 取值 |
|---|---|
| 主题色 | Violet 600 / 700（Tailwind 默认 `violet` 色阶） |
| 中性色 | Slate 50–950 |
| 严重度色 | Critical `#dc2626` / High `#ea580c` / Medium `#ca8a04` / Low `#0891b2` / Info `#64748b` |
| 字体栈（正文） | `-apple-system` / `Segoe UI` / `PingFang SC` / `Microsoft YaHei` |
| 字体栈（代码） | `JetBrains Mono` / `Fira Code` / `Cascadia Code` / `Consolas` |
| 暗色模式 | `<html class="dark">` 切换，由 Alpine.js 切换按钮触发；初次加载跟随 `prefers-color-scheme` |
| 卡片样式 | 圆角 `rounded-xl` + 微阴影 + 4px 左侧严重度色条 |
| 打印 | A4 / `page-break-inside: avoid` / 隐藏导航与切换按钮（`@media print`） |
| 单文件体积 | ~3.9 MB（未压缩），gzip 后约 1 MB |

## 5.3 报告章节结构

```
1. 顶部导航 (sticky)
   - Logo + 版本号
   - 锚点导航（概览 / 仪表盘 / 框架画像 / 漏洞详情 / 附录）
   - 模式徽章 + 主题切换按钮

2. 封面 (cover)
   - 项目名 / 目标 / 模式 / 测试周期 / 生成时间
   - 漏洞总数 + 严重度分布

3. 执行摘要 (summary)
   - LLM 生成总结（含 partial / snippet 警告）
   - 关键发现 Top 5（按严重度 + CVSS 排序）

4. 风险仪表盘 (dashboard)
   - 5 张严重度统计卡
   - Chart.js 环形图（严重度分布）
   - Chart.js 水平柱状图（漏洞类型 Top 10）
   - 覆盖率 / HTTP 入口数 / 高危依赖数

5. 框架画像 (framework)
   - 技术栈识别（语言 / 框架 / 构建工具 / 主入口 / HTTP 入口数）
   - 入口文件清单
   - HTTP 路由表（方法 / URL / 控制器 / 文件 / 鉴权）
   - 高危第三方依赖表

6. 漏洞目录 (findings index)
   - 可折叠；按序号、标题、严重度、CVSS、CWE、文件位置排列

7. 漏洞详情 (findings list)
   - 每个 finding 一张卡片：
     a. 标题 + 严重度色条 + ID
     b. 徽章（severity / confidence / CVSS / CWE / OWASP / 需人工复核）
     c. Meta 信息（文件 / 类路由 / URL / 参数 / 语言 / 发现时间）
     d. 描述 / 影响 / 攻击者能力
     e. 调用链 — Tab 切换：
        - 树形（高亮文本，连接线）
        - Mermaid 流程图（flowchart TD，sink 节点红色高亮）
     f. 漏洞代码块（Prism 高亮，文件路径标题栏）
     g. 复现步骤
     h. PoC（curl / Python / Java / Unit Test，按 Tab 切换）
     i. 修复建议（Before / After 并排）
     j. 参考链接（CWE / OWASP / CVE / NVD）
   - 顶部严重度过滤条（All / Critical / High / Medium / Low / Info）

8. 附录 (appendix)
   - 6.1 代码资产清单
   - 6.2 Agent 执行日志
   - 6.3 工具与版本
   - 6.4 关于黑盒联动（待开发）

9. 免责声明 (disclaimer)
10. 页脚
```

## 5.4 数据契约 / 占位符

模板由 `scripts/render_report.py` 渲染，输入文件：

| 文件 | 类型 | 顶层格式 |
|---|---|---|
| `--findings` | JSON | `[Finding, ...]` 或 `{"findings": [Finding, ...]}` |
| `--assets` | JSON | `[Asset, ...]` 或 `{"assets": [Asset, ...]}` |
| `--profile` | JSON | `FrameworkProfile`（dict） |
| `--execution-log` | 文本 | plain log |

CLI 调用与 v1.0 完全兼容，仅 `--report-template` 改为 `--template-dir`（默认 `templates/`）。

### 模板上下文（renderer 暴露给 Jinja）

```python
{
    "version": "1.0.0",
    "project_name": str, "target": str, "mode": str, "mode_label": str,
    "report_date": "YYYY-MM-DD HH:MM:SS",
    "test_date_start": str, "test_date_end": str,
    "partial": bool, "snippet_mode": bool,
    "primary_language": str, "frameworks": str, "build_tool": str,
    "entry_file": str, "entry_points": [EntryPoint, ...],
    "routes": [Asset, ...], "routes_count": int,
    "deps_count": int, "deps_risk": [DepRisk, ...], "deps_risk_count": int,
    "findings": [Finding, ...], "findings_count": int,
    "counts": {"critical": int, "high": int, "medium": int, "low": int, "info": int},
    "coverage_pct": "85.0", "tested_assets": int, "total_assets": int,
    "severity_filters": ["All", "Critical", "High", "Medium", "Low", "Info"],
    "top_findings": [...], "class_labels_json": str, "class_counts_json": str,
    "executive_summary_intro": HTML 片段,
    "assets": [Asset, ...], "execution_log": str,
    "tool_versions": dict, "tool_versions_purpose": dict,
    "inline": {
        "tailwind_js": str, "alpine_js": str, "chart_js": str,
        "mermaid_js": str, "prism_css": str, "prism_*_js": str, ...
    },
}
```

## 5.5 Finding 字段约定

每个 finding 在模板里是 normalized dict（renderer 会补默认值、跑脱敏、截断过长 snippet、映射 `prism_lang`）：

```python
{
    "id": "FND-0001",
    "title": str,
    "severity": "Critical" | "High" | "Medium" | "Low" | "Informational",
    "confidence": str | None,
    "cvss_score": float | None,
    "cwe": ["CWE-89"] | "CWE-89" | None,
    "owasp_2021": str | None,
    "owasp_api_2023": str | None,
    "language": "java" | "python" | ...,
    "framework": str | None,
    "vuln_class": str,
    "file_path": str,
    "file_line": int | None,
    "class_or_route": str | None,
    "url_or_path": str | None,
    "method": str | [str, ...] | None,
    "parameter": str | None,
    "discovered_at": str | None,
    "description": str,
    "impact": str | None,
    "business_impact": str | None,
    "attacker_capability": str | None,
    "call_chain": [{"symbol": str, "file": str, "line": int}, ...] | None,
    "code_snippet": str | None,
    "reproduction_steps": [str, ...] | None,
    "evidence": {
        "poc_curl": str | None,
        "poc_python": str | None,
        "poc_java": str | None,
        "poc_unit_test": str | None,
        "poc_payload": str | None,
    } | None,
    "remediation": {
        "summary": str | None,
        "code_before": str | None,
        "code_after": str | None,
        "reference": str | None,
    } | None,
    "human_review": bool | None,
    "prism_lang": "java" | "python" | ...,  # renderer 自动填充
}
```

## 5.6 snippet 模式特殊处理

`mode=snippet` 时（`--snippet-mode`）：

- 封面 TARGET 字段显示 `<inline code>` / SIZE N 行
- 省略"代码资产清单"
- 漏洞详情中：`file_path=snippet` / `file_line=相对行号`
- 顶部黄色 banner：`⚠ 代码片段审计 — 仅基于片段内容，缺调用链上下文`
- finding 卡片中无 call_chain 时整段不渲染

## 5.7 脱敏规则（renderer 自动应用）

1. Bearer / Basic / Token 关键字后的长串 → 前 6 + `***` + 末 4
2. 任意 32 字符以上的 base64-ish → 前 6 + `***` + 末 4
3. 内网 IP（10.x / 192.168.x / 172.16-31.x）→ `<internal-ip>`
4. code_snippet 超过 30 行 → 保留头 15 + `... (truncated) ...` + 尾 15

## 5.8 自检清单

生成报告前 Agent / CI 必须确认：

- [ ] 所有 finding 有 `file_path` + `file_line`
- [ ] 所有 High+ 有 `remediation.code_before` + `code_after`
- [ ] 所有 Critical 标记 `human_review=true`
- [ ] 报告中无明文凭据（脱敏规则生效）
- [ ] 图表数据正确（与 findings.json 一致）
- [ ] snippet 模式有 `snippet_mode=true` 标记
- [ ] 增量模式有 `base_commit` / `head_commit` 标记（planned）
- [ ] 免责声明完整
- [ ] 报告 HTML 通过 `tests/smoke_test.py`（27/27 断言）
- [ ] 无 `cdn.jsdelivr.net` / `unpkg.com` 等外部资源引用（单文件离线）
- [ ] 单文件大小 < 6 MB（当前 fixture 实测 3.9 MB）

## 5.9 自定义与扩展

如需修改报告外观：

- **改模板**：直接编辑 `templates/base.html.j2` / `templates/partials/*.html.j2` / `templates/finding.html.j2`
- **改 CSS**：Tailwind utility 写在模板里；少量自定义组件写在 `templates/base.css`
- **改内联资源**：编辑 `scripts/build_inline.py` 的 `ASSETS` dict，然后 `python scripts/build_inline.py --force` 重下
- **添加 finding 字段**：编辑 `scripts/render_report.py` 的 `normalize_finding()`，以及对应模板中的引用
- **更换图标**：模板中所有 inline SVG（heroicons 风格）可直接替换

## 5.10 历史

| 版本 | 日期 | 关键变更 |
|---|---|---|
| v1.0 | - | 初始版：手写 HTML/CSS + `template.replace()` 字符串模板 |
| v1.1 | 2026-06-16 | Jinja2 模板化；Tailwind v4 + Alpine.js + Chart.js + Mermaid.js + Prism.js 全内联；新增严重度过滤 / 主题切换 / call-chain tab；重构 renderer；新增 `build_inline.py` 与 `tests/smoke_test.py` |