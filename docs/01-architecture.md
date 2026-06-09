# 01 — 架构与工作流

## 1.1 总体目标

VioletEyes 的目标是在**不一次性拉全仓库**的前提下，让 LLM Agent 自主完成：

```
语言/框架识别 → 入口定位 → 步进式读代码 → sink/source 追踪 → 可达性推理 → 报告
```

## 1.2 系统组件

```
┌──────────────────────────────────────────────────────────────┐
│                      LLM Agent (AuditBot)                    │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Recon     │  │   Reader    │  │   Static Analyzer   │  │
│  │  (Phase 1)  │→ │  (Phase 3)  │→ │     (Phase 4)       │  │
│  │ ls / tree   │  │  read_queue │  │ sink/source match   │  │
│  │ read        │  │  步进式     │  │ LLM 推理            │  │
│  │ manifests   │  │             │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │                │                  │                │
│         ▼                ▼                  ▼                │
│  framework_profile    read_set         findings.json          │
│      .json            (去重)           (候选 + 过滤)          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Report Renderer (Phase 5)                  │ │
│  │   templates/report.html  ←  findings / assets / profile │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
   code-audit-report.html
```

## 1.3 五阶段流水线

### Phase 1 — Recon
- 列出 `<root>` 顶层（深度 2-3）
- 读取所有 manifest：
  - `pom.xml` / `build.gradle` / `build.gradle.kts`
  - `requirements.txt` / `pyproject.toml` / `setup.py` / `Pipfile`
  - `composer.json`
  - `package.json`
  - `go.mod`
  - `Gemfile`
  - `*.csproj` / `*.sln`
  - `Cargo.toml`
- 写出 `framework_profile.json`：
  ```json
  {
    "languages": ["java"],
    "primary_language": "java",
    "frameworks": ["spring-boot", "mybatis"],
    "build_tool": "maven",
    "entry_points": ["src/main/java/com/x/Application.java"],
    "config_files": ["application.yml", "application.properties"],
    "test_dirs": ["src/test/java"],
    "third_party_deps_count": 42,
    "has_docker": true,
    "has_ci": true
  }
  ```

### Phase 2 — Entry Discovery
按 `signatures/entry-point-patterns.md` 在仓库内匹配入口：
- Spring: `@SpringBootApplication` / `public static void main`
- Django: `ROOT_URLCONF` / `urls.py` / `path(...)`
- Express: `app.listen` / `app.use` / `express()`
- Laravel: `routes/web.php` / `routes/api.php` / `Route::`
- Gin: `gin.Default()` / `r.GET` / `r.POST`
- Rails: `Rails.application.routes.draw` / `config/routes.rb`
- Vue: `createApp` / `app.mount` / `Vue.use(router)`
- React: `ReactDOM.createRoot` / `<BrowserRouter>` / `createBrowserRouter`

输出 `assets.json` 草稿，每个 asset 形如：
```json
{
  "id": "AST-0001",
  "type": "controller",
  "language": "java",
  "framework": "spring-boot",
  "path": "src/main/java/com/x/UserController.java",
  "class_or_route": "UserController",
  "http_method": "GET",
  "url_or_path": "/api/user/{id}",
  "auth_required": true,
  "params": [
    {"name": "id", "location": "path", "type": "numeric"}
  ],
  "tags": ["user-data", "pii"]
}
```

### Phase 3 — Step-wise Reading

**核心规则**：永远不要 `cat -r`，永远不要 `Read .` 整个目录。

#### Read Queue 数据结构

```python
read_queue = deque()  # 待读取文件队列
read_set = set()      # 已读文件去重
in_flight = set()     # 正在读（防重入）

def enqueue(path, reason):
    if path not in read_set and path not in in_flight:
        read_queue.append((path, reason))

def pop_next():
    path, reason = read_queue.popleft()
    in_flight.add(path)
    return path, reason

def mark_done(path, content):
    read_set.add(path)
    in_flight.discard(path)
    # 在这里执行 sink/source 匹配，决定是否入队新文件
    new_paths = analyze(content, path)
    for p in new_paths:
        enqueue(p, reason=f"imported by {path}")
```

#### 读取策略

1. **入口优先**：先读 `framework_profile.entry_points[0]`
2. **调用图展开**：找到文件内 `import / require / use / include` → 入队
3. **框架扫描**：如果是 Controller/Router 文件 → 入队所有 `@GetMapping` 指向的方法所在类
4. **依赖收敛**：同一文件被多处 import，只读一次
5. **token 预算**：每读一个文件 +1 个成本单位（粗略按行数/100 计），超过 `token_budget * 0.8` 立刻停止

#### 文件大小处理

```python
def read_file_safely(path, max_lines=1500):
    size = os.path.getsize(path)
    if size < 100_000:  # 约 1500 行
        return [Read(path)]
    chunks = []
    offset = 0
    while True:
        content = Read(path, offset=offset, limit=max_lines)
        if not content.strip():
            break
        chunks.append(content)
        offset += max_lines
        if offset > 10_000:  # 单文件超过 10000 行强制截断
            break
    return chunks
```

### Phase 4 — Static Analysis

每读完一个文件，立刻：

#### 4.1 sink 模式匹配
按 `signatures/dangerous-functions.md` 列出每种语言的危险函数清单，用 LLM 内置知识匹配（不需要 grep 工具）：

```python
SINK_PATTERNS = {
    "java": {
        "RCE": [r"Runtime\.getRuntime\(\)\.exec", r"ProcessBuilder\(", r"ObjectInputStream"],
        "SQLi": [r"\.createStatement\(\)", r"\.executeQuery\(.*\+", r"@Query\(.*\+" ],
        "DESER": [r"ObjectInputStream", r"XMLDecoder", r"XStream", r"SnakeYaml", r"Yaml\(\)"],
        "SSRF": [r"new URL\(", r"HttpClient\.new", r"RestTemplate", r"WebClient"],
        "CMD":  [r"Runtime\.getRuntime", r"ProcessBuilder", r"\.exec\("],
        "LFI":  [r"new FileInputStream", r"Paths\.get", r"File\(.*getParameter"],
        ...
    },
    "python": {
        "RCE": [r"\beval\(", r"\bexec\(", r"pickle\.load", r"yaml\.load\(.*Loader\s*\=\s*None\)"],
        "SQLi": [r"\.raw\(", r"\.execute\(.*%.*%", r"f\".*SELECT.*\{", r"\.raw\(\""],
        "CMD":  [r"os\.system", r"subprocess\..*shell\s*=\s*True", r"os\.popen"],
        ...
    },
    ...
}
```

LLM 实际执行时**不需要跑 regex**，而是通过文件内容理解触发判断。

#### 4.2 反向追溯

每个 sink 命中，LLM 反向问：
- 这个 sink 接收的参数从何而来？
- 链路是：HTTP body / query / header / cookie / path → 中间变量 → sink
- 中间是否有净化？（如 `PreparedStatement` / `?` 占位符 / `htmlspecialchars` / `JSON.stringify` / 白名单）

#### 4.3 可达性判断

LLM 输出：
```json
{
  "is_reachable": true | false,
  "trust_boundary_crossed": "public_internet" | "internal" | "auth" | "trusted",
  "purification": "none" | "partial" | "full",
  "exploit_likelihood": "trivial" | "easy" | "medium" | "hard",
  "impact": "rce" | "lfi" | "sqli_read" | "sqli_write" | "ssrf" | "xss_reflected" | "xss_stored" | "info_leak" | "auth_bypass",
  "confidence": "Confirmed" | "High" | "Medium" | "Low"
}
```

只有 `is_reachable=true` 才进 findings.json。

### Phase 5 — Report

读取 `templates/report.html` → 替换占位符 → 写入 `<source>/code-audit-report.html`。

## 1.4 snippet 模式

`source` 是文本片段（无目录结构）时：

```
1. 跳过 Phase 1（Recon）/ Phase 2（Entry Discovery）
2. 进入特殊流程：
   a. 用文件内容比例 / 正则识别语言
   b. 在片段内找 sink + 推测 source（基于参数命名 / 注释 / 上下文）
   c. 直接进入 Phase 4 推理
   d. finding 中：asset.type="snippet" / path="<inline>" / file_offset=0
3. 报告标题改为"代码片段审计"
```

## 1.5 性能与 token 节流

| 措施 | 节省 |
|---|---|
| 只读 manifest + 入口 + 调用链关键文件 | 节省 80% |
| offset/limit 分块读大文件 | 节省 30% |
| 已读文件去重 | 节省 15% |
| 不读 test / docs / build 输出 | 节省 20% |
| 早期停止（命中 token 预算 80%） | 防止爆炸 |

## 1.6 失败模式与降级

| 失败 | 降级策略 |
|---|---|
| 无 manifest | 改用扩展名比例启发式 |
| 仓库 > 5GB | 仅扫 manifest + 顶层结构 |
| 找不到入口 | 退化为扫所有 controller / router 命名的文件 |
| snippet 模式无 import 上下文 | 标注 confidence ≤ Medium |
| token 预算耗尽 | 立刻出报告，标 partial=true |

## 1.7 黑盒联动（待开发）

VioletEyes 的 finding JSON 在 `url_or_path` / `method` / `parameter` 字段中保留了
与未来配套黑盒方向 Skill 兼容的命名约定，便于将来在合并归档时直接对齐。

**当前状态：待开发。** 配套的黑盒 Skill 尚未实现，本 Skill 不会调用任何外部黑盒服务。
上述字段在当前版本中仅作结构化记录，无任何下游消费方。
