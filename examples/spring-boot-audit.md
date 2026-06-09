# Example: Spring Boot + MyBatis 全量审计

> 演示对一个真实 Spring Boot + MyBatis 项目做完整审计的全过程。
> 输入：`./example-projects/spring-boot-user-api`
> 输出：`./code-audit-report.html` + `findings.json` + `assets.json` + `framework_profile.json`

## 1. 项目结构（待审计目标）

```
spring-boot-user-api/
├── pom.xml
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── com/example/
│   │   │       ├── UserApiApplication.java
│   │   │       ├── controller/
│   │   │       │   └── UserController.java
│   │   │       ├── service/
│   │   │       │   └── UserService.java
│   │   │       ├── repository/
│   │   │       │   ├── UserRepository.java
│   │   │       │   └── UserMapper.java
│   │   │       ├── entity/
│   │   │       │   └── User.java
│   │   │       └── util/
│   │   │           └── SearchUtil.java
│   │   └── resources/
│   │       ├── application.yml
│   │       └── mapper/
│   │           └── UserMapper.xml
│   └── test/
└── Dockerfile
```

## 2. Agent 调用流程

### 2.1 触发

用户输入：
```
请使用 code-audit-skill 审计 ./example-projects/spring-boot-user-api
```

### 2.2 Phase 1: 侦察

```bash
$ python3 scripts/tree_index.py ./example-projects/spring-boot-user-api --depth 3
[OK] tree written to tree.json
     total: 14
     by class: {'java': 6, 'config': 2, 'xml': 1, 'sql': 0, 'build': 1}

$ python3 scripts/framework_detect.py ./example-projects/spring-boot-user-api
[OK] profile written to framework_profile.json
     primary_language: java
     frameworks: ['spring-boot', 'mybatis']
     entry_points: 1
     dangerous_dependencies: 0
```

`framework_profile.json` 摘录：
```json
{
  "primary_language": "java",
  "frameworks": ["spring-boot", "mybatis"],
  "build_tool": "maven",
  "entry_points": [
    {
      "path": "src/main/java/com/example/UserApiApplication.java",
      "symbol": "com.example.UserApiApplication",
      "framework": "spring-boot",
      "annotations": ["@SpringBootApplication"]
    }
  ],
  "config_files": ["src/main/resources/application.yml"]
}
```

### 2.3 Phase 2: 入口定位

Agent 读 `UserApiApplication.java`：
```java
@SpringBootApplication
public class UserApiApplication {
    public static void main(String[] args) {
        SpringApplication.run(UserApiApplication.class, args);
    }
}
```

读 `UserController.java`：
```java
@RestController
@RequestMapping("/api/users")
public class UserController {
    @Autowired
    private UserService userService;

    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }

    @PostMapping("/search")
    public List<User> search(@RequestParam String keyword) {
        return userService.searchByName(keyword);
    }

    @PostMapping
    public User create(@RequestBody UserDTO dto) {
        return userService.create(dto);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        userService.delete(id);
    }
}
```

Agent 抽取 routes：
```json
[
  {"method": "GET",    "path": "/api/users/{id}",   "handler": "UserController.getUser",     "auth": false},
  {"method": "POST",   "path": "/api/users/search", "handler": "UserController.search",      "auth": false},
  {"method": "POST",   "path": "/api/users",        "handler": "UserController.create",      "auth": false},
  {"method": "DELETE", "path": "/api/users/{id}",   "handler": "UserController.delete",      "auth": false}
]
```

### 2.4 Phase 3: 步进式读取

Agent read_queue 顺序：
1. `UserController.java`（已读）
2. `UserService.java`（imports from controller）
3. `UserRepository.java` / `UserMapper.java` / `UserMapper.xml`（imports from service）
4. `SearchUtil.java`（imports from service）
5. `User.java`（entity）
6. `application.yml`（config）

逐步读取并对每个文件调 `sink_detect.py`：

```bash
$ python3 scripts/sink_detect.py UserService.java --json
[
  {
    "line": 28,
    "name": "sqli-orm-raw",
    "cwe": "CWE-89",
    "severity": "High",
    "context": "searchByName(String keyword) { return userMapper.searchByName(\"%\" + keyword + \"%\"); }"
  }
]

$ python3 scripts/sink_detect.py UserMapper.xml --json
[
  {
    "line": 8,
    "name": "sqli-mybatis-dollar",
    "cwe": "CWE-89",
    "severity": "High",
    "context": "<select id=\"searchByName\" resultType=\"User\">SELECT * FROM users WHERE name LIKE '${value}'</select>"
  }
]

$ python3 scripts/sink_detect.py UserRepository.java --json
[
  {
    "line": 22,
    "name": "idor-direct-findById",
    "cwe": "CWE-639",
    "severity": "High",
    "context": "@Query(\"SELECT u FROM User u WHERE u.id = \" + id)"
  }
]

$ python3 scripts/sink_detect.py SearchUtil.java --json
[
  {
    "line": 14,
    "name": "deser-snakesql-yaml-or-xstream",
    "cwe": "CWE-94",
    "severity": "Critical",
    "context": "YAML yaml = new YAML(); Object o = yaml.load(searchFilter);"
  }
]

$ python3 scripts/sink_detect.py application.yml --json
[]
```

### 2.5 Phase 4: LLM 推理

Agent 读取每个文件后做可达性分析：

#### Finding 1: SQL Injection in searchByName

```yaml
finding:
  id: FND-0001
  title: UserController.search 存在 SQL 注入（MyBatis ${}）
  file: src/main/resources/mapper/UserMapper.xml
  file_line: 8
  call_chain:
    - UserController.search(@RequestParam String keyword)         # line 25
    - UserService.searchByName(keyword)                            # line 28
    - userMapper.searchByName("%" + keyword + "%")                 # line 30
    - XML mapper: <select id="searchByName">WHERE name LIKE '${value}'</select>  # line 8  ← 漏洞
  source: @RequestParam String keyword  (HTTP query)
  sanitization: NONE  (#{} 才是参数化)
  exploit_likelihood: Trivial
  impact: SQL injection (read)
  confidence: Confirmed
  severity: High
  cwe: CWE-89
  owasp: A03:2021
  url_or_path: /api/users/search
  method: POST
  parameter: keyword
```

修复建议：
```xml
<!-- Before -->
<select id="searchByName" resultType="User">
    SELECT * FROM users WHERE name LIKE '${value}'
</select>

<!-- After -->
<select id="searchByName" resultType="User">
    SELECT * FROM users WHERE name LIKE CONCAT('%', #{value}, '%')
</select>
```

#### Finding 2: IDOR in getUser / delete

```yaml
finding:
  id: FND-0002
  title: UserController.getUser/delete 存在 IDOR 漏洞
  file: UserController.java
  call_chain:
    - UserController.getUser(@PathVariable Long id)         # line 18
    - UserService.findById(id)                              # line 12
    - userRepository.findById(id)                           # line 22 (直接传)
  source: @PathVariable Long id (公开)
  sanitization: NONE  (无 owner 校验)
  auth_required: false
  severity: High
  cwe: CWE-639
  owasp: A01:2021 / API1:2023
```

修复建议：
```java
// Before
@GetMapping("/{id}")
public User getUser(@PathVariable Long id) {
    return userService.findById(id);
}

// After
@GetMapping("/{id}")
@PreAuthorize("@userSecurity.hasAccess(#id, principal)")
public User getUser(@PathVariable Long id) {
    return userService.findById(id);
}
```

#### Finding 3: SnakeYAML 反序列化 RCE

```yaml
finding:
  id: FND-0003
  title: SearchUtil.loadSearchFilter 存在 SnakeYAML 反序列化 RCE
  file: src/main/java/com/example/util/SearchUtil.java
  file_line: 14
  call_chain:
    - UserController.search(@RequestParam String keyword)    # line 25
    - UserService.searchByName(keyword)                       # line 28
    - searchUtil.parseFilter(searchFilter)                    # line 35
    - YAML().load(searchFilter)                               # line 14  ← 漏洞
  source: 外部输入（可能是 header / cookie）
  severity: Critical
  cwe: CWE-502
  owasp: A08:2021
  exploit_likelihood: Trivial
  impact: RCE
  confidence: Confirmed
  vuln_class: deserialization-java
```

修复：
```java
// Before
Yaml yaml = new Yaml();
Object o = yaml.load(searchFilter);

// After
Yaml yaml = new Yaml(new SafeConstructor(new LoaderOptions()));
Object o = yaml.load(searchFilter);
```

#### Finding 4: Mass Assignment in create

```yaml
finding:
  id: FND-0004
  title: UserController.create 存在 Mass Assignment
  ...
  severity: Medium
  cwe: CWE-915
  owasp: A04:2021
```

修复：使用 DTO 而非直接绑定 User entity。

#### Finding 5: application.yml 含 log4j 旧版

由于 `pom.xml` 不含 log4j，跳过。

### 2.6 Phase 5: 报告

```bash
$ python3 scripts/render_report.py \
    --findings findings.json \
    --assets assets.json \
    --profile framework_profile.json \
    --execution-log execution.log \
    --output code-audit-report.html \
    --project-name "spring-boot-user-api" \
    --target "./example-projects/spring-boot-user-api" \
    --mode full

[OK] report written to code-audit-report.html
     total findings: 4
```

## 3. 报告样例（节选）

```html
<section id="FND-0003" class="finding severity-Critical">
  <header class="finding-header">
    <span class="id">FND-0003</span>
    <h3>SearchUtil.loadSearchFilter 存在 SnakeYAML 反序列化 RCE</h3>
    <span class="badge severity-Critical">Critical</span>
    <span class="badge confidence">Confirmed</span>
    <span class="badge cvss">CVSS 9.8</span>
    <span class="badge cwe">CWE-502</span>
    <span class="badge owasp">A08:2021</span>
    <span class="badge language">java</span>
    <span class="badge framework">spring-boot</span>
  </header>

  <div class="finding-meta">
    <span class="label">文件:</span><code>src/main/java/com/example/util/SearchUtil.java:14</code>
    <span class="label">类:</span><code>SearchUtil.loadSearchFilter</code>
    <span class="label">URL:</span><code>POST /api/users/search</code>
    <span class="label">参数:</span><code>searchFilter (header)</code>
  </div>

  <h4>📋 描述</h4>
  <p>SearchUtil 类使用 <code>new Yaml().load(...)</code> 反序列化外部传入的 YAML 字符串。
     SnakeYAML 默认使用 <code>Constructor</code>，允许实例化任意 Java 类，
     攻击者可通过精心构造的 YAML gadget 链执行任意代码。</p>

  <h4>🔗 调用链</h4>
  <pre><code class="language-yaml">UserController.search(@RequestParam String keyword)        # UserController.java:25
  └─ UserService.searchByName(keyword)                       # UserService.java:28
      └─ searchUtil.parseFilter(searchFilter)                # UserService.java:35
          └─ YAML().load(searchFilter)                       # SearchUtil.java:14  ← 漏洞</code></pre>

  <h4>📝 vulnerable code</h4>
  <pre><code class="language-java">// SearchUtil.java:14-16
public static SearchFilter parseFilter(String yaml) {
    Yaml y = new Yaml();
    return y.loadAs(yaml, SearchFilter.class);
}</code></pre>

  <h4>🔧 修复建议</h4>
  <pre><code class="language-java">// Before
public static SearchFilter parseFilter(String yaml) {
    Yaml y = new Yaml();
    return y.loadAs(yaml, SearchFilter.class);
}

// After (方案 1：SafeConstructor)
public static SearchFilter parseFilter(String yaml) {
    Yaml y = new Yaml(new SafeConstructor(new LoaderOptions()));
    return y.loadAs(yaml, SearchFilter.class);
}

// After (方案 2：根本不用 YAML，改 JSON)
public static SearchFilter parseFilter(String json) throws IOException {
    return new ObjectMapper().readValue(json, SearchFilter.class);
}</code></pre>

  <h4>🛠️ PoC</h4>
  <pre><code class="language-bash">curl -X POST 'http://target:8080/api/users/search' \
  -H 'Content-Type: application/json' \
  -d '{"keyword":"!!javax.script.ScriptEngineManager []"}'</code></pre>

  <h4>📚 参考</h4>
  <ul>
    <li>CWE-502: <a href="https://cwe.mitre.org/data/definitions/502.html">Deserialization of Untrusted Data</a></li>
    <li>OWASP Top 10 2021: A08 - Software and Data Integrity Failures</li>
    <li><a href="https://github.com/google/security-research-pocs">SnakeYAML gadget examples</a></li>
  </ul>
</section>
```

## 4. 关键学习点

1. **步进读取** — 6 个核心文件全读完，< 3000 行，远小于"Read 整个仓库"
2. **sink 模式匹配** — `sink_detect.py` 帮 LLM 圈出 4 个候选，LLM 进一步判断可达性
3. **调用链追溯** — LLM 从 controller 一路追到 XML mapper，发现真正的 sink 在 XML
4. **修复建议** — 提供具体可粘贴的代码（不是"加 WAF"）
5. **PoC** — 给出 curl 文本但 Agent 不直接执行

## 5. 与 pentestskill 协同

将 FND-0003 的 `url_or_path` / `method` / `parameter` 喂给 pentestskill：

```
请用 pentestskill 验证以下目标：
POST /api/users/search (searchFilter header)
```

pentestskill 会构造请求验证 RCE，确认可利用性。两份报告并排归档。
