# 06 — LLM 静态分析原理

> 为什么这个 Skill 不直接用 grep / semgrep？  
> 因为 LLM 的推理能力是**最关键的可达性判断者**。

## 6.1 模式匹配的局限

```python
# 看似危险
query = "SELECT * FROM users WHERE id = " + user_input
cursor.execute(query)
```

模式匹配器会立刻标红。LLM 推理后会问：

- `user_input` 真的来自用户吗？还是程序启动时固定的常量？
- 中间是否有净化？例如 `int(user_input)` 强转？
- `cursor` 是 `Cursor.execute` 还是 `LoggingCursor`（安全 wrapper）？
- 数据库是否有特殊防护？如查询超时、SQL firewall？

```python
# 看似安全
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_input,))
```

模式匹配器忽略。LLM 推理后发现：

- `cursor` 实际是 `psycopg2.extensions.cursor` 的子类，重写了 `execute` 但**先拼接再执行**？
- `user_input` 进入了 `sqlalchemy.text(query)` 但**未绑定参数**？
- `cursor.execute(query, params)` 但 `params` 被实现忽略？

LLM 的"语义理解"是 SAST 是否能落地的核心。

## 6.2 LLM 分析的三个层次

### 第一层：模式识别（Pattern Match）
LLM 内化执行 `signatures/dangerous-functions.md` 的规则。

输入：源码片段  
输出：候选 sink 列表（位置 + 类别）

### 第二层：调用链追溯（Call Chain Tracing）
LLM 反向问：

- 这个 sink 的参数从何而来？
- 它被谁调用？
- 调用者是否做净化？

输入：候选 sink + 已读文件  
输出：可达性判定（reachable / unreachable / uncertain）

### 第三层：业务上下文（Business Context）
LLM 进一步问：

- 这是公开接口还是内部接口？
- 是否需要鉴权？是否实际校验？
- 攻击者能否触发？
- 触发的代价和影响？

输入：可达 sink + 路由表 + 鉴权注解 / 中间件  
输出：完整 finding（severity / confidence / 影响）

## 6.3 推理模板（Agent 实际内化）

每命中一个 sink，LLM 在"思考"阶段做以下推理：

```markdown
### sink 识别
- 文件: UserRepository.java:12
- 模式: `@Query("...")` + 字符串拼接
- 类别: JPA SQLi (CWE-89)

### 数据流追溯
- 上游 1: UserController.getUser(@PathVariable Long id)  # line 42
- 上游 2: UserService.findById(id)                       # line 18
- 上游 3: UserRepository.findById(id) → 触发本 sink
- `id` 类型为 `Long`，但**未在 @Query 中用 :id 命名参数**而是字符串拼接

### 净化检查
- @PathVariable 注解本身不做 SQL 转义
- Long 类型转换仅防止部分注入，但**拼接绕过类型检查后仍可注入**（编译期决定，不影响运行时 SQL）
- 实际风险：高

### 业务上下文
- URL: GET /api/user/{id}
- 鉴权: @PreAuthorize("hasAuthority('USER')")  # 任意登录用户可访问
- 影响: 任意用户查询任意 ID（IDOR + SQLi）

### 评级
- Severity: High (SQLi 读 + IDOR)
- Confidence: Confirmed
- Exploitability: Easy
- Impact: Major
```

## 6.4 LLM 分析的局限与降级

LLM 推理**不擅长的**：

| 局限 | 表现 | 缓解 |
|---|---|---|
| 长调用链断裂 | 跨 10 层调用时容易漏 | 显式提示 Agent 维护 call_chain |
| 框架魔法 | Spring AOP / NestJS Guards 在源码层不可见 | 读 framework 配置文件补足 |
| 动态语言反射 | Ruby send / Python __import__ | 标 confidence=Low + human_review |
| 混淆/压缩代码 | min.js / 加密字符串 | 不审计 + 提示用户 |
| 大型 monorepo | 跨模块依赖复杂 | 限定 scope 优先 |
| 第三方库内部 | 不读 node_modules | 改用 manifest + CVE 库 |

## 6.5 LLM 分析的优势

LLM 推理**擅长的**：

| 优势 | 表现 |
|---|---|
| 上下文敏感 | 同一个 `eval` 在沙箱中 vs 公开接口 = 完全不同风险 |
| 隐式净化识别 | ORM `where(name: x)` 表面是函数调用但内部用占位符 |
| 业务逻辑 | "用户提交订单后未支付，再次提交能否修改金额？" — 需理解业务流 |
| 命名语义 | `userInput` vs `sanitizedUsername` — 直接从命名判断 |
| 注释理解 | `// 内部调用，不对外开放` 等注释 |
| 框架惯例 | Spring Security 默认防护 / Django ORM 默认参数化 |

## 6.6 调用链产出物

每个 finding 必含 `call_chain` 数组：

```json
"call_chain": [
  {
    "file": "UserController.java",
    "line": 42,
    "symbol": "UserController.getUser",
    "snippet": "public User getUser(@PathVariable Long id) {"
  },
  {
    "file": "UserService.java",
    "line": 18,
    "symbol": "UserService.findById",
    "snippet": "public User findById(Long id) {"
  },
  {
    "file": "UserRepository.java",
    "line": 12,
    "symbol": "UserRepository.findById",
    "snippet": "@Query(\"SELECT u FROM User u WHERE u.id = \" + id)"
  }
]
```

Agent 在推理时构造这个数组，render_report.py 把它渲染成可读的代码块。

## 6.7 与 semgrep / codeql 的可选协同

虽然本 Skill 不强制依赖，但 Agent **可以**先跑本地 semgrep 加速：

```bash
semgrep --config=p/security-audit --json /path/to/repo > /tmp/semgrep.json
```

然后把 semgrep 命中的位置作为**入队点**（read_queue 的高优先级成员），LLM 再深入分析。这能减少 LLM 的扫描工作量。

类似地，CodeQL 数据库预先生成后，Agent 可用 `codeql query run` 做数据流分析，输出作为 finding 候选。

## 6.8 自我对账（Self-Audit）

LLM 在生成报告前必须做：

1. **覆盖检查**：
   - 已读文件数 / 估计总文件数 = coverage
   - coverage < 50% → 报告标 partial=true
2. **合理性检查**：
   - finding 数 = 0 时不要硬凑"low" finding
   - finding 数 > 50 时检查是否有重复 / 同源 / 同 sink
3. **修复建议可执行**：
   - code_after 必须能 compile（不引未导入的类）
   - 修复必须针对本 finding 的根因，不是"加 WAF"
4. **CWE 准确**：
   - SQLi → CWE-89（不是 CWE-20 输入验证）
   - XSS → CWE-79（不是 CWE-79 + CWE-20 叠加）
   - 反序列化 → CWE-502
5. **CVSS 合理**：
   - SQLi 写 + 无鉴权 = 9.8
   - Reflected XSS 自打 = 6.1
   - 缺失安全头 = 3.7 (Low)

## 6.9 推理的"硬约束"清单

Agent 在做"可达性"判断时，下列规则**必须**遵守：

1. **绝对不能**因为 sink 出现在文件里就直接标 finding
2. **必须**尝试追溯 source（即使 source 不在已读文件中）
3. **必须**考虑框架默认防护（如 Spring Security 默认开启 CSRF）
4. **必须**考虑隐式净化（`int()` / `escape()` / ORM 参数化）
5. **必须**给出 confidence，不允许"看起来像就标 Critical"
6. **必须**给出人类可读的 PoC，不允许"用 sqlmap 跑一下"
7. **必须**给出可粘贴的修复代码，不允许"加个白名单"
