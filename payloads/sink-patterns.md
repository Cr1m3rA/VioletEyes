# Sink 模式库

> Agent 在 Phase 4 (Mining) 阶段用 LLM 推理匹配。
> 详细列表见 [signatures/dangerous-functions.md](../signatures/dangerous-functions.md)。

## 1. 分类总览

按危险度分 4 档：

| 档 | 类型 | 命中后即候选 |
|---|---|---|
| 🔴 Critical | RCE / 反序列化 / 鉴权绕过 | 直接进入 finding 候选 |
| 🟠 High | 注入 / 文件 / SSRF / IDOR | 大概率进入候选 |
| 🟡 Medium | XSS / Open Redirect / CSRF / 业务逻辑 | 视上下文 |
| 🟢 Low | 配置 / 信息泄露 / 弱加密 | 视上下文 |

## 2. 各语言 Top 10 sink

### Java 🔴
1. `Runtime.getRuntime().exec` / `ProcessBuilder` 拼接
2. `ObjectInputStream.readObject` / `XMLDecoder` / `XStream.fromXML`
3. `new Yaml().load` (SnakeYaml)
4. `JSON.parse` (Fastjson < 1.2.83)
5. `InitialContext.lookup` (JNDI)
6. `SpelExpressionParser` / OGNL evaluate
7. `@Query` / `@Select` 字符串拼接
8. `DocumentBuilderFactory` 未禁用 DTD (XXE)
9. `new URL` / `RestTemplate` 用户输入 (SSRF)
10. `response.getWriter().write` 用户输入 (XSS)

### Python 🔴
1. `eval` / `exec`
2. `pickle.load` / `pickle.loads`
3. `yaml.load` (无 SafeLoader)
4. `subprocess.*(shell=True)` 拼接
5. `os.system` / `os.popen` 拼接
6. `render_template_string` 拼接
7. `cursor.execute("..." + user_input)` 拼接
8. `open(".../" + user_input)` 路径遍历
9. `requests.get(user_input)` SSRF
10. `importlib.import_module(user_input)` 任意模块

### PHP 🔴
1. `eval` / `assert`
2. `unserialize`
3. `system` / `exec` / `passthru` / 反引号
4. `include` / `require` 动态参数
5. `mysql_query` 拼接
6. `file_get_contents` 用户输入
7. `header("Location: $user_input")`
8. `echo $_GET[...]`
9. `preg_replace /e`
10. `move_uploaded_file` 路径写入

### JavaScript / TypeScript 🔴
1. `eval` / `new Function`
2. `child_process.exec` 拼接
3. `_.merge` / `_.set` (lodash prototype pollution)
4. `node-serialize.unserialize`
5. `yaml.load` (无 schema)
6. `db.query` 拼接
7. `fs.readFile` 路径遍历
8. `fetch(userInput)` / `axios.get(userInput)` SSRF
9. `innerHTML = userInput` / `v-html` / `dangerouslySetInnerHTML`
10. `Math.random()` 用于 token

### Go 🔴
1. `exec.Command("sh", "-c", user_input)`
2. `http.Get(user_input)` / `http.NewRequest(user_input, ...)`
3. `os.Open("/data/" + user_input)` 路径遍历
4. `db.Query("... " + user_input)` SQL 拼接
5. `template.HTML(user_input)` XSS
6. `math/rand` 用于 token
7. `c.Query` / `c.PostForm` 透传到 sink

### Ruby 🔴
1. `eval` / `instance_eval` / `class_eval`
2. `system(user_input)` / 反引号 `` `#{user_input}` ``
3. `YAML.load(user_input)`
4. `Marshal.load(user_input)`
5. `User.where("name = '#{params[:name]}'")` 字符串插值
6. `ERB.new(user_input)`
7. `File.read("/data/" + user_input)` 路径遍历
8. `send(user_input, *args)` 动态方法

### C# 🔴
1. `Process.Start("cmd.exe", "/c " + user_input)`
2. `BinaryFormatter.Deserialize(stream)` / `JavaScriptSerializer.Deserialize<object>(json)`
3. `new SqlCommand("... " + user_input)` 拼接
4. `XmlDocument.Load(user_input)` 未禁用 DTD
5. `new HttpClient().GetAsync(user_input)` SSRF
6. `File.ReadAllText("/data/" + user_input)` 路径遍历
7. `@Html.Raw(user_input)` XSS
8. `Random` 用于 token

## 3. 跨语言共性

### SQL 注入 sink（多语言）
| 语言 | 危险 | 安全替代 |
|---|---|---|
| Java | `Statement.executeQuery("..." + x)` | `PreparedStatement` + `?` |
| Java | `@Query("..." + x)` (JPA) | `@Query("... :param")` |
| Java | `@Select("... ${x}")` (MyBatis) | `@Select("... #{x}")` |
| Python | `cursor.execute("..." + x)` | `cursor.execute("... ?", (x,))` |
| Python | `User.objects.filter("name = '" + x + "'")` | `User.objects.filter(name=x)` |
| Python | `User.objects.raw("... " + x)` | 用 ORM |
| Node | `db.query("... " + x)` | `db.query("... ?", [x])` |
| PHP | `mysql_query("... " . $x)` | `mysqli_query($c, "... ?", [$x])` (PDO) |
| Go | `db.Query("... " + x)` | `db.Query("... $1", x)` |
| Ruby | `User.where("name = '#{x}'")` | `User.where(name: x)` |
| C# | `new SqlCommand("... " + x)` | `cmd.Parameters.AddWithValue(...)` |

### SSRF sink（多语言）
| 语言 | 危险 |
|---|---|
| Java | `new URL(x).openStream()` / `RestTemplate.getForObject(x, ...)` |
| Python | `requests.get(x)` / `urllib.request.urlopen(x)` |
| Node | `fetch(x)` / `axios.get(x)` |
| PHP | `file_get_contents(x)` / `curl_setopt($ch, CURLOPT_URL, x)` |
| Go | `http.Get(x)` |
| Ruby | `Net::HTTP.get(URI(x))` |
| C# | `new HttpClient().GetAsync(x)` |

**SSRF bypass 检查清单**：
- [ ] scheme 限制为 http/https（防 file:// / gopher://）
- [ ] 域名/IP 白名单（防 169.254.169.254 / 127.0.0.1 / 10.x / 192.168.x）
- [ ] 阻止 DNS rebinding（解析后再次校验 IP）
- [ ] 阻止 redirect（`allow_redirects=False`）
- [ ] 仅返回必要数据（防止内部信息泄露）

### 反序列化 sink（多语言）
| 语言 | 危险 | 安全替代 |
|---|---|---|
| Java | `ObjectInputStream.readObject()` | 自写白名单 |
| Java | `XMLDecoder.readObject()` | JAXB + schema |
| Java | `XStream.fromXML(x)` | 设置 `addPermission(NoTypePermission.NONE)` + 白名单 |
| Java | `new Yaml().load(x)` | `new Yaml(new SafeConstructor())` |
| Java | `JSON.parse(x)` (Fastjson) | `JSON.parse(x, Feature.SupportAutoType)` 不开启 |
| Python | `pickle.load(x)` | `json.load(x)` |
| Python | `yaml.load(x)` | `yaml.load(x, Loader=yaml.SafeLoader)` |
| Python | `marshal.load(x)` | 不用 |
| PHP | `unserialize(x)` | `json_decode(x)` |
| Node | `node-serialize.unserialize(x)` | `JSON.parse(x)` |
| Node | `yaml.load(x)` (js-yaml) | `yaml.load(x, { schema: yaml.JSON_SCHEMA })` |
| Go | `gob.NewDecoder(r).Decode(&v)` | 自定义 codec |
| Ruby | `YAML.load(x)` | `YAML.safe_load(x)` |
| Ruby | `Marshal.load(x)` | 不用 |
| C# | `BinaryFormatter().Deserialize(s)` | `System.Text.Json` + 强类型 |

### XSS sink（前端）
| 框架 | 危险 | 安全替代 |
|---|---|---|
| Vue 2/3 | `v-html="x"` | `{{ x }}`（自动转义） |
| React | `dangerouslySetInnerHTML={{__html: x}}` | `{x}` |
| React | `<a href={x}>` 且 x 以 `javascript:` 开头 | 校验协议 |
| Angular | `[innerHTML]="x"` + `bypassSecurityTrustHtml(x)` | 仅用 [innerHTML] |
| Svelte | `{@html x}` | `{x}` |
| jQuery | `$('.x').html(x)` | `$('.x').text(x)` |
| Vanilla | `element.innerHTML = x` | `element.textContent = x` |
| Vanilla | `document.write(x)` | 不用 |
| Vanilla | `location.href = x` (javascript:) | 校验协议 |

### 路径遍历 sink（多语言）
| 语言 | 危险 | 缓解 |
|---|---|---|
| Java | `new File("/data/" + x)` | `FilenameUtils.getName(x)` 后校验 |
| Java | `new FileInputStream("/data/" + x)` | 同上 |
| Python | `open("/data/" + x)` | `os.path.realpath` 后校验在白名单内 |
| Node | `fs.readFile("/data/" + x)` | `path.resolve` + 校验 |
| PHP | `file_get_contents("/data/" + x)` | `basename(x)` + 白名单 |
| Go | `os.Open("/data/" + x)` | `filepath.Clean` + 白名单 |
| Ruby | `File.read("/data/" + x)` | `File.expand_path` + 白名单 |
| C# | `File.ReadAllText("/data/" + x)` | `Path.GetFileName(x)` + 白名单 |

## 4. 调用 sink 模式

### 调用链追踪伪代码

```python
def trace_call_chain(sink_line, sink_file):
    chain = []
    # 1. 在 sink 所在函数内找 sink 调用
    func = enclosing_function(sink_line, sink_file)
    chain.append((sink_file, func.name, sink_line))
    
    # 2. 在同文件 / 同包内找谁调用了 func
    callers = find_callers(func.name, scope=project)
    for caller in callers:
        chain.append((caller.file, caller.func, caller.line))
        # 3. 继续向上追（限制深度 ≤ 5）
        if depth < 5:
            chain.extend(trace_call_chain(caller.line, caller.file))
    
    return chain
```

### 净化检查清单

无论何类 sink，命中后必须问：

1. **入口处是否有校验**？
   - 类型强转：`int(x)` 至少防 SQLi 但不防其他
   - 范围校验：`if not is_valid_id(x): return error`
   - 白名单：`if x in ALLOWED: ...`

2. **中间是否有转义**？
   - HTML: `htmlspecialchars` / `escape` / `encodeURIComponent`
   - SQL: `?` / `#{}` / `:param`
   - Shell: `shlex.quote` / `subprocess` 数组形式
   - Path: `realpath` + 白名单

3. **出口是否有过滤**？
   - CSP header
   - WAF
   - ORM 默认参数化（Django / SQLAlchemy）

4. **是否在受信任上下文**？
   - 同进程内调用 vs HTTP 入口
   - 内部 service vs 公开 API

## 5. 不进入 finding 的常见原因

LLM 在做"是否升为 finding"判断时，下列条件**任一**满足即可降级或排除：

| 条件 | 降级策略 |
|---|---|
| sink 接收的是硬编码常量 | 排除 |
| sink 接收的是同进程内可信值 | 排除 |
| 中间有完整的参数化 / 转义 | 排除 |
| 调用链有白名单校验 | 降 confidence |
| 调用链未读完整 | 标 confidence=Low + human_review |
| 路由不存在 / 未挂载 | 降 severity |
| 仅限内部网络 | 降 severity |
