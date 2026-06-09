# 05 — HTML 审计报告

> 本节定义 VioletEyes 产出的 `code-audit-report.html` 的结构、占位符与渲染规范。

## 5.1 视觉规范

报告为单文件 HTML，自包含样式与脚本（Chart.js 4.4.0 + Prism.js 1.29.0）。
整体配色与排版参考了主流安全报告的视觉语言：

| 维度 | 取值 |
|---|---|
| 主色 | `#1a73e8` |
| 严重度色 | `#dc3545` / `#fd7e14` / `#ffc107` / `#17a2b8` / `#6c757d`（Critical → Informational） |
| 字体栈 | `-apple-system` / `PingFang SC` / `微软雅黑` |
| 代码字体 | `JetBrains Mono` / `Fira Code` / `Consolas` |
| 暗色模式 | 跟随 `prefers-color-scheme: dark` |
| 卡片布局 | `finding-card` + 4px 左侧色条 |
| 打印 | A4 + 11pt + `page-break-inside: avoid` |

> 备注：与配套黑盒方向 Skill 的报告字段命名保持兼容，便于将来合并归档。
> 该 Skill 当前处于待开发状态，因此目前不存在"两份报告并排"的合并场景。

## 5.2 报告结构

```
1. Cover（封面）
   - 项目名（自动取自 manifest 顶层 / Git repo 名 / 用户输入）
   - 报告时间、审计时间
   - 目标范围（仓库路径 / Git URL / "代码片段"）
   - 漏洞统计 + 风险分布
   - 漏洞类型分布
   - 测试方法论

2. Executive Summary
   - LLM 生成 1 段总结
   - 风险 × 数量 表格
   - 关键发现 Top 5

3. 框架画像（VioletEyes 专属）
   - 识别出的语言 / 框架 / 入口
   - 路由表（HTTP 入口）
   - 第三方依赖风险

4. 漏洞详情
   - 每个 finding 一个 <section id="FND-0001" class="finding severity-High">
   - 子内容：
     a. 标题 + 严重度徽章
     b. 文件位置（file_path:line）
     c. 描述
     d. 影响
     e. 调用链（call_chain 数组）
     f. vulnerable code 片段（带行号）
     g. 修复前 / 修复后 代码对比
     h. PoC（curl / 代码片段）
     i. OWASP / CWE 分类
     j. 元数据：发现时间、文件、参数

5. 附录
   - 代码资产清单（routes / controllers / 组件）
   - 入口文件清单
   - 第三方依赖风险清单（Log4Shell 等）
   - Agent 执行日志
   - 工具与版本

6. 免责声明
```

## 5.3 报告占位符

```
{{PROJECT_NAME}}        从 manifest 顶层或 git repo 名推断
{{REPORT_DATE}}         当前时间 (YYYY-MM-DD HH:MM)
{{TEST_DATE_START}}     审计开始时间
{{TEST_DATE_END}}       审计结束时间
{{TARGET}}              仓库路径 / Git URL / "代码片段"
{{SOURCE_TYPE}}         local | git | archive | snippet
{{MODE}}                full | incremental | snippet | api-focused | frontend-focused | diff
{{FRAMEWORK_PROFILE}}   HTML 表格（语言/框架/入口）
{{ROUTES_TABLE}}        HTML 表格（路由表）
{{DEPS_RISK_TABLE}}     HTML 表格（高危依赖）
{{TOTAL_ASSETS}}        代码资产数
{{FINDINGS_COUNT}}      漏洞总数
{{COUNT_CRITICAL}} ...  按严重度计数
{{FINDINGS_LIST}}       漏洞详情 HTML
{{ASSETS_TABLE}}        代码资产表格
{{EXECUTION_LOG}}       Agent 步进日志
{{TOOL_VERSIONS}}       JSON（python、os、llm 等）
{{PARTIAL}}             bool，超 token 预算时为 true
{{COVERAGE}}            实际审计文件数 / 估计总文件数
```

## 5.4 finding 渲染

```html
<section id="FND-0001" class="finding severity-High">
    <header class="finding-header">
        <span class="id">FND-0001</span>
        <h3>UserController.getUser 存在 SQL 注入</h3>
        <span class="badge severity-High">High</span>
        <span class="badge confidence">Confirmed</span>
        <span class="badge cvss">CVSS 8.1</span>
        <span class="badge cwe">CWE-89</span>
        <span class="badge owasp">A03:2021</span>
    </header>

    <div class="finding-meta">
        <span class="label">文件:</span><code>src/main/java/com/x/UserController.java:42</code>
        <span class="label">函数:</span><code>UserController.getUser</code>
        <span class="label">URL:</span><code>GET /api/user/{id}</code>
        <span class="label">参数:</span><code>id</code>
        <span class="label">语言/框架:</span><code>Java / Spring Boot 2.7</code>
    </div>

    <h4>📋 描述</h4>
    <p>...</p>

    <h4>💥 影响</h4>
    <p>...</p>

    <h4>🔗 调用链</h4>
    <pre><code class="language-yaml">UserController.getUser(@PathVariable Long id)        # line 42
  └─ userService.findById(id)                          # line 18
      └─ userRepository.findById(id)                   # line 12
          └─ JPA: createQuery("SELECT u FROM User u WHERE u.id = " + id)  # line 8  ← 漏洞</code></pre>

    <h4>📝 vulnerable code</h4>
    <pre><code class="language-java">// UserController.java:42-46
@GetMapping("/user/{id}")
public User getUser(@PathVariable Long id) {
    return userService.findById(id);   // id 直接透传至 JPA
}</code></pre>

    <h4>🔧 修复建议</h4>
    <h5>Before</h5>
    <pre><code class="language-java">// UserRepository.java:8
@Query("SELECT u FROM User u WHERE u.id = " + id)
User findById(@Param("id") Long id);</code></pre>

    <h5>After</h5>
    <pre><code class="language-java">// UserRepository.java:8
@Query("SELECT u FROM User u WHERE u.id = :id")
User findById(@Param("id") Long id);</code></pre>

    <h4>🛠️ PoC（仅作验证用）</h4>
    <pre><code class="language-bash">curl -X GET 'https://target/api/user/1%20OR%201%3D1' \
  -H 'Authorization: Bearer &lt;token&gt;'</code></pre>

    <h4>📚 参考</h4>
    <ul>
        <li><a href="https://owasp.org/Top10/A03_2021-Injection/">OWASP A03:2021 - Injection</a></li>
        <li><a href="https://cwe.mitre.org/data/definitions/89.html">CWE-89</a></li>
    </ul>
</section>
```

## 5.5 snippet 模式特殊处理

`mode=snippet` 时：

- 封面：TARGET = `<inline code>` / SIZE = N 行
- 省略"代码资产清单"（snippet 没有文件）
- 漏洞详情中：`file_path=snippet` / `file_line=相对行号` / `code_snippet=片段内容`
- 强调"白盒确认"标记：`snippet_mode=true` / `confidence ≤ Medium`
- 顶部 banner：`⚠️ 代码片段审计 — 仅基于片段内容，缺调用链上下文`

## 5.6 脱敏规则

1. 不展示完整 Authorization / Cookie / Token / API Key（前 6 + `***` + 末 4）
2. 不展示真实 IP（10.x / 192.168.x / 172.16-31.x / 内部域名 → `<internal>`）
3. 不展示真实用户名 / 邮箱 / 手机号
4. 代码片段 ≤ 30 行；超长只保留 sink ± 15 行
5. 修复建议代码片段不带任何用户数据
6. 报告不含 `git diff` 中可能含的密钥

## 5.7 自检清单

生成报告前 Agent 必须：

- [ ] 所有 finding 有 file_path + line
- [ ] 所有 High+ 有修复建议（code_before + code_after）
- [ ] 所有 Critical 标记 human_review=true
- [ ] 报告中无明文凭据
- [ ] 图表数据正确（与 findings.json 一致）
- [ ] snippet 模式有 `snippet_mode=true` 标记
- [ ] 增量模式有 `base_commit` / `head_commit` 标记
- [ ] 免责声明完整
- [ ] 报告 HTML 校验通过
- [ ] token 预算未超限（若超，标 partial=true）
