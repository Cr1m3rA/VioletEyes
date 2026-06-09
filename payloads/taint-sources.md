# Taint Source（污染源）速查

> sink 命中后必须追溯 source。
> 本文列出各语言中"用户可控输入"的标准来源。

## 1. 污染源分类

| 类别 | 风险等级 | 来源 |
|---|---|---|
| HTTP 入口 | 高 | 请求体、Query、Header、Cookie、Path |
| 配置 | 中 | env、YAML、JSON、properties |
| 文件 | 中 | 用户上传、读取文件 |
| 数据库 | 中-高 | 旧记录、共享数据库 |
| 第三方 API | 中 | 上游服务的响应 |
| CLI 参数 | 中 | argv、stdin |
| 内部调用 | 低 | 同进程内的 service-to-service |
| 常量 | 极低 | 字面量 |

## 2. 跨语言 source 模式

### Java Spring

```java
// 注解
@PathVariable x
@RequestParam("x") x
@RequestHeader("X-...") x
@CookieValue("xxx") x
@RequestBody SomeDTO x        // 整对象危险

// HttpServletRequest 直接
request.getParameter("x")
request.getHeader("X-...")
request.getCookies()
request.getInputStream()

// @Autowired 注入的 source
@Value("${user.dir}") String userDir
@Value("#{systemProperties['xxx']}") String sysProp
Environment.getProperty("xxx")
```

### Java Servlet

```java
request.getParameter("x")
request.getHeader("X-...")
request.getCookies()
request.getSession().getAttribute("x")
request.getInputStream()  // body
```

### Python Flask

```python
request.args.get("x")           # query
request.form.get("x")           # body
request.files["x"]              # upload
request.headers.get("X-...")
request.cookies.get("x")
request.json                    # JSON body
request.data                    # raw body
request.values                  # args + form
```

### Python Django

```python
request.GET.get("x")
request.POST.get("x")
request.FILES.get("x")
request.COOKIES.get("x")
request.META.get("HTTP_X_...")
request.body                    # raw body
request.path                    # URL path
```

### Python FastAPI

```python
async def handler(
    x: str = Query(...),                # query
    y: str = Form(...),                 # form
    z: SomeModel = Body(...),           # JSON body
    h: str = Header(...),               # header
    cookie: str = Cookie(...),          # cookie
    path_x: int = Path(...),            # path
):
    ...
```

### Node.js Express

```js
req.query.x                    // query
req.body.x                     // body
req.params.x                   // path
req.headers["x"]               // header
req.cookies.x                  // cookie
req.body                       // 整 body 危险
req.file                       // upload (multer)
```

### PHP Laravel

```php
request()->input('x')          // all
request()->query('x')          // query
request()->post('x')           // form
request()->json('x')           // JSON
$request->header('X-...')
$request->cookie('x')
$request->file('x')            // upload
$request->route('x')           // path
$request->all()                // 整对象危险
```

### PHP Symfony

```php
$request->query->get('x')      // query
$request->request->get('x')    // form
$request->headers->get('X-...')
$request->cookies->get('x')
$request->files->get('x')      // upload
$request->getContent()         // raw
```

### Go Gin

```go
c.Query("x")                  // query
c.PostForm("x")                // form
c.Param("x")                   // path
c.GetHeader("X-...")           // header
c.Cookie("x")                  // cookie
c.ShouldBindJSON(&obj)         // JSON body
c.ShouldBind(&obj)             // form
c.Request.URL.Query()          // raw query
c.Request.Body                 // raw body
```

### Go net/http

```go
r.URL.Query().Get("x")
r.FormValue("x")
r.Header.Get("X-...")
r.Cookie("x")
r.Body
r.MultipartReader
```

### Ruby Rails

```ruby
params[:x]                     // all
params["x"]
request.query_parameters[:x]
request.request_parameters[:x]
request.headers["X-..."]
cookies[:x]
```

### C# / .NET

```csharp
Request.Query["x"]              // query
Request.Form["x"]               // form
Request.Headers["X-..."]
Request.Cookies["x"]
Request.Body                    // raw
Request.Params["x"]             // all
routeData.Values["x"]           // path
[FromQuery] string x
[FromBody] SomeModel x
[FromHeader] string x
[FromRoute] string x
[FromForm] string x
```

## 3. 间接 source（配置 / 文件 / DB）

### 环境变量

```python
os.environ.get("X")          # Python
os.Getenv("X")               # Go
process.env.X                # Node
getenv("X")                  # PHP
System.getenv("X")           # Java
ENV["X"]                     # Ruby
```

### 配置文件

```yaml
# application.yml
spring:
  datasource:
    url: ${DB_URL}              # 用户配置
```

如果 `DB_URL` 来自仓库外的 env 注入 → 风险低
如果 `DB_URL` 写死 / 提交进仓库 → 风险高

### 文件

```python
# 用户上传
uploaded_file = request.files["file"]
content = uploaded_file.read()      # 危险：可能是任意二进制
content = uploaded_file.stream.read()

# 本地文件
content = open("/data/" + user_input).read()  # 路径遍历
```

### 数据库

```python
# 从 DB 读取后再用 → 二阶注入
old_name = db.query("SELECT name FROM users WHERE id = " + user_input).name
db.execute("UPDATE x SET name = '" + old_name + "' WHERE id = 1")  # 二阶 SQLi
```

## 4. source 推断的"命名信号"

LLM 在 snippet 模式（无完整调用链）下，依赖变量命名判断 source：

| 命名模式 | 推断 source |
|---|---|
| `userInput`, `user_input`, `username`, `name` | 用户输入 |
| `request.x`, `req.x`, `params.x` | HTTP 输入 |
| `query`, `q` | URL query |
| `body`, `data`, `payload`, `json` | 请求体 |
| `token`, `auth`, `jwt` | 认证头（但被签名，**不是任意输入**） |
| `id`, `userId`, `orderId` | 路径参数 / 引用 |
| `cmd`, `command`, `exec` | 命令参数 |
| `file`, `filename`, `path` | 文件路径 |
| `url`, `uri`, `host`, `domain` | 网络地址 |
| `xml`, `json`, `yaml` | 序列化数据 |
| `config`, `cfg`, `settings` | 配置 |
| `raw`, `unsafe`, `dirty` | 暗示未净化 |
| `sanitized`, `clean`, `safe` | 暗示已净化 |

## 5. 不应视为 source 的

| 模式 | 原因 |
|---|---|
| 字面量 `"abc"` | 不可控 |
| 函数返回的常量 | 不可控 |
| 同进程内 Service 调用 | 通常可信（除非该 Service 自己也接收用户输入） |
| 配置中固定值 | 不可控（除非配置文件用户可改） |
| 编译期常量 | 不可控 |
| JWT 中 claim | 已签名，但**仍可能因为业务设计而含用户输入**（需要分析） |
| 数据库中"系统种子数据" | 通常可信（除非数据来源用户） |

## 6. source → sink 调用链模板

LLM 在 trace 时构造：

```yaml
- layer: 1  # source
  file: UserController.java
  line: 42
  symbol: "UserController.getUser(@PathVariable Long id)"
  type: "@PathVariable"
  sanitization: none
  trust: untrusted

- layer: 2  # service
  file: UserService.java
  line: 18
  symbol: "UserService.findById(Long id)"
  sanitization: none
  trust: propagated

- layer: 3  # repository (sink)
  file: UserRepository.java
  line: 12
  symbol: "UserRepository.findById"
  type: "@Query"
  sanitization: NONE   # ← 漏洞位置
  trust: untrusted
  vuln: SQL injection
```

## 7. 多入口 source 聚合

一个 sink 可能被多个入口触发：

```
UserController.getUser(@PathVariable id)   → UserService.findById  → SQLi
AdminController.searchUser(@RequestParam id) → UserService.findById → SQLi
BatchJob.process(@Value id)                 → UserService.findById → SQLi
```

LLM 应列出所有入口，并在 finding 中说明"影响 N 个入口"。

## 8. source 反向追溯算法（伪代码）

```python
def trace_source(sink_var, file, line, project_root, max_depth=5):
    """反向追溯：sink 接收的变量来自哪里？"""
    chain = []
    cur_var = sink_var
    cur_file = file
    cur_line = line
    
    for depth in range(max_depth):
        # 找 cur_var 在 cur_file 的赋值
        assignment = find_assignment(cur_var, cur_file)
        if not assignment:
            break
        chain.append({
            "file": cur_file,
            "line": assignment.line,
            "expression": assignment.expr,
            "source_type": classify_source(assignment.expr),
        })
        # 如果是用户输入，停止
        if is_user_input(assignment.expr):
            break
        # 否则继续追溯 assignment 右侧的变量
        new_var = extract_root_var(assignment.expr)
        if new_var == cur_var:
            break
        cur_var = new_var
        # 追溯到 caller 函数
        caller = find_enclosing_caller(assignment.line, cur_file, project_root)
        if caller:
            cur_file = caller.file
            cur_line = caller.line
        else:
            break
    
    return chain
```
