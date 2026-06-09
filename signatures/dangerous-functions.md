# 危险函数 / Sink 速查

> Agent 在 Phase 4 (Mining) 阶段用 LLM 推理匹配。
> 完整漏洞分类见 [docs/04-vulnerability-catalog.md](../docs/04-vulnerability-catalog.md)。

## 1. Java

### RCE / 命令执行

| sink | 危险 | CWE |
|---|---|---|
| `Runtime.getRuntime().exec(...)` | 拼接用户输入 → 命令执行 | CWE-78 |
| `new ProcessBuilder(...).start()` | 同上 | CWE-78 |
| `ProcessBuilder.command(args...)` 数组中含用户输入 | 数组形式不拼接，相对安全 | - |
| `System.loadLibrary(userInput)` | 加载任意动态库 | CWE-114 |
| `JNI` / `native` 方法 | 调用 native | CWE-111 |

### 反序列化

| sink | 危险 | CWE |
|---|---|---|
| `ObjectInputStream.readObject()` | 反序列化 gadget | CWE-502 |
| `XMLDecoder.readObject()` | XML 反序列化 | CWE-502 |
| `XStream.fromXML(...)` | XML 反序列化（默认接受任意类） | CWE-502 |
| `new Yaml().load(string)` | YAML 反序列化 | CWE-502 |
| `SnakeYaml Yaml.loadAs(...)` | YAML 反序列化 | CWE-502 |
| `Hessian2Input.readObject(...)` | Hessian 反序列化 | CWE-502 |
| `JSON.parse(...)` (Fastjson < 1.2.83) | JSON 反序列化 | CWE-502 |
| `ObjectMapper.readValue(json, Object.class)` (Jackson with default typing) | JSON 反序列化 | CWE-502 |
| `Kryo.readObject(...)` | 二进制反序列化 | CWE-502 |
| `FST` / `Jboss Marshalling` | 反序列化 | CWE-502 |
| `java.beans.XMLDecoder` | XMLDecoder 反序列化 | CWE-502 |

### JNDI

| sink | 危险 | CWE |
|---|---|---|
| `InitialContext.lookup("ldap://..."+userInput)` | JNDI 注入 → RCE | CWE-502 |
| `Context.lookup(userInput)` | 同上 | CWE-502 |

### SpEL / OGNL / EL

| sink | 危险 | CWE |
|---|---|---|
| `SpelExpressionParser().parseExpression(userInput).getValue()` | SpEL 注入 | CWE-94 |
| `ExpressionParser.parseExpression(userInput)` (Spring 早期) | 同上 | CWE-94 |
| `Ognl.getValue(userInput, ...)` (Struts2) | OGNL 注入 | CWE-94 |
| `OgnlContext.getValue(userInput)` | 同上 | CWE-94 |
| `ApplicationContext.getBean(userInput)` | Bean 注入 | CWE-94 |

### SQL 注入

| sink | 危险 | CWE |
|---|---|---|
| `Statement.executeQuery("SELECT ..." + userInput)` | 字符串拼接 | CWE-89 |
| `Connection.prepareStatement(sql + userInput)` | 拼接后再预编译 | CWE-89 |
| `@Query("SELECT u FROM User u WHERE u.name = '" + name + "'")` | JPA 字符串拼接 | CWE-89 |
| `@Select("SELECT * FROM x WHERE id = ${id}")` (MyBatis) | `${}` 替换 | CWE-89 |
| `JdbcTemplate.query("... " + sql)` | JdbcTemplate 拼接 | CWE-89 |
| `EntityManager.createNativeQuery("..." + userInput)` | 原生 SQL 拼接 | CWE-89 |
| `NamedParameterJdbcTemplate.queryForObject(sqlMap.get("key")+userInput, ...)` | 同上 | CWE-89 |

### SSTI / 模板注入

| sink | 危险 | CWE |
|---|---|---|
| `TemplateEngine.process(userInput, ctx)` (Freemarker) | 模板注入 | CWE-94 |
| `Velocity.evaluate(ctx, writer, "name", userInput)` | Velocity 注入 | CWE-94 |
| `Thymeleaf` 模板字符串拼接 | SSTI | CWE-94 |

### SSRF

| sink | 危险 | CWE |
|---|---|---|
| `new URL(userInput).openStream()` | SSRF | CWE-918 |
| `HttpURLConnection` / `URLConnection` 接收用户 URL | SSRF | CWE-918 |
| `new RestTemplate().getForObject(userInput, ...)` | SSRF | CWE-918 |
| `WebClient.create().get().uri(userInput)` | SSRF | CWE-918 |
| `HttpClient.newBuilder().build().send(HttpRequest.newBuilder(URI.create(userInput))...)` | SSRF | CWE-918 |
| `okhttp3.OkHttpClient.newBuilder().url(userInput)` | SSRF | CWE-918 |
| `org.apache.http.client.methods.HttpGet(userInput)` | SSRF | CWE-918 |
| `Jsoup.connect(userInput).get()` | SSRF | CWE-918 |
| `ImageIO.read(new URL(userInput))` | SSRF | CWE-918 |

### XXE

| sink | 危险 | CWE |
|---|---|---|
| `DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(...)` 未禁用外部实体 | XXE | CWE-611 |
| `SAXParserFactory.newInstance().newSAXParser().parse(...)` | XXE | CWE-611 |
| `XMLInputFactory.newFactory().createXMLStreamReader(...)` | XXE | CWE-611 |
| `TransformerFactory.newInstance().newTransformer().transform(...)` | XXE | CWE-611 |
| `SchemaFactory.newInstance(...)` | XXE | CWE-611 |
| `Validator.validate(new StreamSource(userInput))` | XXE | CWE-611 |
| `JAXBContext.createUnmarshaller().unmarshal(userInput)` | XXE | CWE-611 |

### 路径 / 文件

| sink | 危险 | CWE |
|---|---|---|
| `new File(userInput)` | 路径遍历 | CWE-22 |
| `new FileInputStream("/data/" + userInput)` | 路径遍历 | CWE-22 |
| `Paths.get(baseDir, userInput)` | 路径遍历 | CWE-22 |
| `RandomAccessFile(userInput, "r")` | 路径遍历 | CWE-22 |
| `Files.readAllBytes(Paths.get("/data/" + userInput))` | 路径遍历 | CWE-22 |
| `MultipartFile.transferTo(new File("/upload/" + filename))` | 上传路径写入 | CWE-22 |
| `new FileOutputStream("/upload/" + filename)` | 同上 | CWE-22 |
| `Files.write(Paths.get("/upload/" + filename), bytes)` | 同上 | CWE-22 |

### XSS（服务端）

| sink | 危险 | CWE |
|---|---|---|
| `response.getWriter().write(userInput)` 无转义 | Reflected XSS | CWE-79 |
| `HttpServletResponse.getOutputStream().print(userInput)` | 同上 | CWE-79 |
| `ModelAndView` addObject 含未转义 userInput | SSTI | CWE-79 |
| Thymymeleaf `th:utext="${userInput}"` | XSS | CWE-79 |
| JSP `<%= userInput %>` 无转义 | XSS | CWE-79 |
| JSP `${userInput}` (EL) 无转义 | XSS | CWE-79 |

### Open Redirect

| sink | 危险 | CWE |
|---|---|---|
| `response.sendRedirect(userInput)` | Open Redirect | CWE-601 |
| `response.setStatus(302); response.setHeader("Location", userInput)` | Open Redirect | CWE-601 |

### 头部注入 / CRLF

| sink | 危险 | CWE |
|---|---|---|
| `response.setHeader(name, userInput)` 含 `\r\n` | Header 注入 | CWE-93 |
| `response.addHeader(name, userInput)` | 同上 | CWE-93 |

### Crypto / 弱加密

| sink | 危险 | CWE |
|---|---|---|
| `MessageDigest.getInstance("MD5")` | 弱哈希 | CWE-327 |
| `MessageDigest.getInstance("SHA-1")` | 弱哈希 | CWE-327 |
| `Cipher.getInstance("DES")` | 弱加密 | CWE-327 |
| `Cipher.getInstance("RC4")` | 弱加密 | CWE-327 |
| `Cipher.getInstance("AES/ECB/...")` | 弱模式（推荐 GCM） | CWE-327 |
| `new SecureRandom()` | 安全 | - |
| `new Random()` | 不安全随机（用于 token） | CWE-338 |

### 硬编码密钥

| sink | 危险 | CWE |
|---|---|---|
| `String secret = "abc123..."` | 硬编码 | CWE-798 |
| `byte[] key = "12345678".getBytes()` | 硬编码 | CWE-798 |
| `properties.getProperty("password")` 来自 properties 文件（提交进仓库） | 密钥泄露 | CWE-798 |

### Log4j (Log4Shell)

| sink | 危险 | CWE |
|---|---|---|
| `log.info(userInput)` (log4j 2.0~2.14.1) | `${jndi:ldap://...}` 触发 RCE | CVE-2021-44228 |
| `logger.info(userInput)` | 同上 | CVE-2021-44228 |
| `LOGGER.log(Level.INFO, userInput)` | 同上 | CVE-2021-44228 |
| `logger.error(userInput)` | 同上 | CVE-2021-44228 |
| `MDC.put("key", userInput)` | 同上（写入 MDC 后再格式化） | CVE-2021-44228 |
| `ThreadContext.put("key", userInput)` | 同上 | CVE-2021-44228 |
| 任何写入 log4j 日志的字符串 | 若 log4j-core < 2.15.0 即风险 | CVE-2021-44228 |

## 2. Python

### RCE / eval

| sink | 危险 | CWE |
|---|---|---|
| `eval(userInput)` | RCE | CWE-94 |
| `exec(userInput)` | RCE | CWE-94 |
| `compile(source, filename, mode)` + `exec` | RCE | CWE-94 |
| `ast.literal_eval(userInput)` | **安全**（仅字面量） | - |

### 命令执行

| sink | 危险 | CWE |
|---|---|---|
| `os.system("ls " + userInput)` | 命令注入 | CWE-78 |
| `os.popen("ls " + userInput)` | 同上 | CWE-78 |
| `subprocess.call("ls " + userInput, shell=True)` | shell=True 注入 | CWE-78 |
| `subprocess.Popen("ls " + userInput, shell=True)` | 同上 | CWE-78 |
| `subprocess.run("ls " + userInput, shell=True)` | 同上 | CWE-78 |
| `commands.getoutput("ls " + userInput)` (Py2) | 同上 | CWE-78 |
| `subprocess.call(["ls", userInput])` | **数组形式安全** | - |
| `subprocess.run(["ls", userInput])` | 同上 | - |

### 反序列化

| sink | 危险 | CWE |
|---|---|---|
| `pickle.load(open(file, 'rb'))` | 反序列化 RCE | CWE-502 |
| `pickle.loads(data)` | 反序列化 RCE | CWE-502 |
| `cPickle.loads(data)` (Py2) | 同上 | CWE-502 |
| `_pickle.loads(data)` | 同上 | CWE-502 |
| `yaml.load(data)` | YAML 反序列化（默认） | CWE-502 |
| `yaml.load(data, Loader=yaml.Loader)` | YAML 反序列化 | CWE-502 |
| `yaml.load(data, Loader=yaml.FullLoader)` | YAML 反序列化（仍支持 Python 特定标签） | CWE-502 |
| `yaml.load(data, Loader=yaml.SafeLoader)` | **安全** | - |
| `marshal.load(open(file, 'rb'))` | marshal RCE | CWE-502 |
| `shelve.open(file)` | pickle 后端 | CWE-502 |
| `dill.loads(data)` | 同 pickle | CWE-502 |

### SQL 注入

| sink | 危险 | CWE |
|---|---|---|
| `cursor.execute("SELECT * FROM x WHERE id = " + user_input)` | 拼接 | CWE-89 |
| `cursor.execute(f"SELECT * FROM x WHERE id = {user_input}")` | f-string | CWE-89 |
| `cursor.execute("SELECT * FROM x WHERE id = %s" % user_input)` | % 格式化 | CWE-89 |
| `cursor.execute("SELECT * FROM x WHERE id = ?", (user_input,))` | **参数化安全** | - |
| `Model.objects.filter(f"name = '{name}'")` (Django) | 拼接 | CWE-89 |
| `Model.objects.raw(f"SELECT * FROM x WHERE name = '{name}'")` | 原生 SQL 拼接 | CWE-89 |
| `Model.objects.extra(where=[f"name = '{name}'"])` | extra 拼接 | CWE-89 |
| `connection.execute(text("..." + user_input))` (SQLAlchemy) | text() 拼接 | CWE-89 |

### NoSQL 注入

| sink | 危险 | CWE |
|---|---|---|
| `users.find({"username": user, "password": pwd})` 且 `user = {"$ne": null}` | NoSQL 注入 | CWE-943 |
| `users.find({"$where": "this.name == '" + user + "'"})` | `$where` 注入 | CWE-943 |
| `users.find({"$or": [...]})` 用户输入 | `$or` 注入 | CWE-943 |
| `db.users.find_one(request.json)` | 整对象透传 | CWE-943 |

### SSTI

| sink | 危险 | CWE |
|---|---|---|
| `render_template_string("Hello, " + user_input)` | Jinja2 SSTI | CWE-94 |
| `flask.render_template_string(f"Hello, {user_input}")` | 同上 | CWE-94 |
| `jinja2.Template("Hello, " + user_input).render()` | 同上 | CWE-94 |
| `jinja2.Environment().from_string(user_input).render()` | 同上（高危） | CWE-94 |
| `tornado.template.Template(user_input).generate()` | Tornado SSTI | CWE-94 |
| `mako.template.Template(user_input).render()` | Mako SSTI | CWE-94 |

### SSRF

| sink | 危险 | CWE |
|---|---|---|
| `requests.get(userInput)` | SSRF | CWE-918 |
| `urllib.request.urlopen(userInput)` | SSRF | CWE-918 |
| `httpx.get(userInput)` | SSRF | CWE-918 |
| `aiohttp.ClientSession().get(userInput)` | SSRF | CWE-918 |
| `http.client.HTTPConnection(host=...).request(...)` | SSRF | CWE-918 |

### XXE

| sink | 危险 | CWE |
|---|---|---|
| `xml.etree.ElementTree.fromstring(userInput)` | 早期 Python 风险 | CWE-611 |
| `lxml.etree.parse(userInput)` (旧版) | XXE | CWE-611 |
| `lxml.etree.fromstring(userInput, parser=...)` 配置 `resolve_entities=True` | XXE | CWE-611 |
| `xml.sax.parseString(...)` (旧版) | XXE | CWE-611 |
| `xmlrpc.client.loads(...)` | XXE | CWE-611 |

### 路径 / 文件

| sink | 危险 | CWE |
|---|---|---|
| `open("/data/" + user_input)` | 路径遍历 | CWE-22 |
| `os.path.join("/data", user_input)` | 路径遍历（不防护 ../） | CWE-22 |
| `shutil.copy(user_input, "/data/")` | 路径遍历 | CWE-22 |
| `shutil.rmtree("/data/" + user_input)` | 危险 + 路径遍历 | CWE-22 |
| `subprocess.run(["rm", "-rf", "/data/" + user_input])` | 任意删除 | CWE-22 |
| `zipfile.ZipFile(user_input).extractall("/data/")` | Zip Slip | CWE-22 |
| `tarfile.open(user_input).extractall("/data/")` | Zip Slip | CWE-22 |

### 反序列化 (Django 特殊)

| sink | 危险 | CWE |
|---|---|---|
| `pickle.loads(session_data)` (Django session backend) | 任意反序列化 | CWE-502 |
| `yaml.load(request.data)` (Django) | 反序列化 | CWE-502 |

### Crypto / 弱加密

| sink | 危险 | CWE |
|---|---|---|
| `hashlib.md5(password)` | 弱哈希 | CWE-327 |
| `hashlib.sha1(password)` | 弱哈希 | CWE-327 |
| `random.random()` 用于 token / salt | 不安全随机 | CWE-338 |
| `random.choice(...)` 用于 token | 不安全随机 | CWE-338 |
| `secrets.token_*` | **安全** | - |

### 硬编码 / 配置

| sink | 危险 | CWE |
|---|---|---|
| `SECRET_KEY = "abc123"` (Django settings) | 硬编码密钥 | CWE-798 |
| `ALLOWED_HOSTS = ['*']` | Host header injection | CWE-644 |
| `DEBUG = True` | 信息泄露 | CWE-489 |
| `app.run(debug=True)` | 远程控制台 (Werkzeug PIN) | CWE-489 |
| `verify=False` (requests) | TLS 验证关闭 | CWE-295 |

## 3. PHP

### RCE / eval

| sink | 危险 | CWE |
|---|---|---|
| `eval($userInput)` | RCE | CWE-94 |
| `assert($userInput)` (PHP < 8) | RCE | CWE-94 |
| `preg_replace("/pattern/e", $userInput, ...)` (PHP < 7) | RCE | CWE-94 |
| `create_function('$a', $userInput)` (PHP < 7.2) | RCE | CWE-94 |
| `array_map($userInput, ...)` (callback) | 任意函数调用 | CWE-94 |
| `array_filter($array, $userInput)` | 任意函数调用 | CWE-94 |
| `usort($array, $userInput)` | 任意函数调用 | CWE-94 |

### 命令执行

| sink | 危险 | CWE |
|---|---|---|
| `system($userInput)` | RCE | CWE-78 |
| `exec($userInput)` | RCE | CWE-78 |
| `passthru($userInput)` | RCE | CWE-78 |
| `popen($userInput, "r")` | RCE | CWE-78 |
| `proc_open($userInput, ...)` | RCE | CWE-78 |
| `shell_exec($userInput)` | RCE | CWE-78 |
| 反引号 `` `cmd` `` | RCE | CWE-78 |
| `pcntl_exec($userInput)` | RCE | CWE-78 |

### 反序列化

| sink | 危险 | CWE |
|---|---|---|
| `unserialize($userInput)` | 反序列化 gadget 链 | CWE-502 |
| `unserialize($userInput, ['allowed_classes' => false])` (PHP 7+) | 缓解（需白名单） | - |
| `phar://$userInput` 协议触发 | 间接反序列化 | CWE-502 |

### SQL 注入

| sink | 危险 | CWE |
|---|---|---|
| `mysql_query("SELECT * FROM x WHERE id = " . $userInput)` | 拼接 | CWE-89 |
| `mysqli_query($conn, "SELECT * FROM x WHERE id = " . $userInput)` | 同上 | CWE-89 |
| `mysqli_query($conn, "SELECT * FROM x WHERE id = $userInput")` | 双引号插值 | CWE-89 |
| `->query("SELECT ... " . $userInput)` (PDO) | 拼接 | CWE-89 |
| `DB::select("SELECT * FROM x WHERE id = " . $userInput)` (Laravel) | 拼接 | CWE-89 |
| `DB::select("SELECT * FROM x WHERE id = ?", [$userInput])` | **参数化安全** | - |
| `Model::whereRaw("name = '" . $userInput . "'")` (Laravel) | 拼接 | CWE-89 |
| `Model::whereRaw("name = ?", [$userInput])` | **安全** | - |

### SSTI

| sink | 危险 | CWE |
|---|---|---|
| `View::addLocation($userInput)` (Laravel) | 模板路径 | CWE-94 |
| `Blade::render($userInput)` | 模板注入 | CWE-94 |
| `$twig->createTemplate("Hello, " . $userInput)->render()` | Twig SSTI | CWE-94 |
| `eval("echo $userInput;")` 风格 include | RCE | CWE-94 |

### SSRF

| sink | 危险 | CWE |
|---|---|---|
| `file_get_contents($userInput)` | SSRF | CWE-918 |
| `fopen($userInput, "r")` | SSRF | CWE-918 |
| `curl_setopt($ch, CURLOPT_URL, $userInput)` | SSRF | CWE-918 |
| `curl_init($userInput)` | SSRF | CWE-918 |
| `get_headers($userInput)` | SSRF | CWE-918 |

### 路径 / 文件

| sink | 危险 | CWE |
|---|---|---|
| `include($userInput)` | LFI / RFI | CWE-829 |
| `include_once($userInput)` | LFI / RFI | CWE-829 |
| `require($userInput)` | LFI / RFI | CWE-829 |
| `require_once($userInput)` | LFI / RFI | CWE-829 |
| `file_get_contents("/data/" . $userInput)` | 路径遍历 | CWE-22 |
| `file_put_contents("/upload/" . $userInput, $data)` | 路径遍历 + 写入 | CWE-22 |
| `fopen("/data/" . $userInput, "r")` | 路径遍历 | CWE-22 |
| `readfile("/data/" . $userInput)` | 路径遍历 | CWE-22 |
| `unlink("/data/" . $userInput)` | 任意删除 | CWE-22 |
| `move_uploaded_file($_FILES['f']['tmp_name'], "/upload/" . $userInput)` | 上传路径写入 | CWE-22 |
| `chmod("/data/" . $userInput, 0777)` | 权限滥用 | CWE-732 |

### 头部注入

| sink | 危险 | CWE |
|---|---|---|
| `header("Location: " . $userInput)` | Open Redirect | CWE-601 |
| `header("Set-Cookie: name=" . $userInput)` | Header 注入 | CWE-93 |
| `header("X-Custom: " . $userInput)` | Header 注入 | CWE-93 |
| `mail($to, $subject, $body, $headers, $userInput)` | 邮件头注入 | CWE-93 |

### XSS

| sink | 危险 | CWE |
|---|---|---|
| `echo $_GET['x']` | Reflected XSS | CWE-79 |
| `print $_POST['x']` | 同上 | CWE-79 |
| `<?= $userInput ?>` 无 htmlspecialchars | XSS | CWE-79 |
| Blade `{!! $userInput !!}` | XSS (不转义) | CWE-79 |
| Twig `{{ $userInput | raw }}` | XSS | CWE-79 |
| `<?= htmlspecialchars($userInput) ?>` | **安全** | - |

### Crypto

| sink | 危险 | CWE |
|---|---|---|
| `md5($password)` | 弱哈希 | CWE-327 |
| `sha1($password)` | 弱哈希 | CWE-327 |
| `crypt($password, $salt)` 单轮 DES | 弱 | CWE-327 |
| `password_hash($password, PASSWORD_DEFAULT)` | **安全** | - |
| `mt_rand()` 用于 token | 不安全随机 | CWE-338 |
| `rand()` 用于 token | 不安全随机 | CWE-338 |
| `random_bytes($n)` | **安全** | - |

### 危险配置

| 配置 | 风险 |
|---|---|
| `display_errors = On` | 信息泄露 |
| `expose_php = On` | 版本泄露 |
| `allow_url_include = On` | RFI |
| `allow_url_fopen = On` | SSRF（file_get_contents 用户 URL） |
| `register_globals = On` (PHP 5.4 移除) | 变量覆盖 |
| `magic_quotes_gpc = On` (PHP 5.4 移除) | 已废弃，勿信 |

## 4. JavaScript / TypeScript

### RCE / eval

| sink | 危险 | CWE |
|---|---|---|
| `eval(userInput)` | RCE | CWE-94 |
| `new Function(userInput)()` | RCE | CWE-94 |
| `setTimeout(userInput, ms)` (string 形式) | RCE | CWE-94 |
| `setInterval(userInput, ms)` | RCE | CWE-94 |
| `setImmediate(userInput)` | RCE | CWE-94 |
| `vm.runInThisContext(userInput)` | RCE | CWE-94 |
| `vm.runInNewContext(userInput)` | RCE | CWE-94 |

### 反序列化

| sink | 危险 | CWE |
|---|---|---|
| `node-serialize.unserialize(userInput)` | RCE (IIFE) | CWE-502 |
| `js-yaml.load(userInput)` | YAML RCE | CWE-502 |
| `js-yaml.load(userInput, { schema: yaml.JSON_SCHEMA })` | **安全** | - |
| `js-yaml.load(userInput, { schema: yaml.CORE_SCHEMA })` | **相对安全**（不支持类型） | - |
| `serialize-javascript` 反序列化 + RCE 链 | RCE | CWE-502 |

### 原型链污染

| sink | 危险 | CWE |
|---|---|---|
| `_.merge(target, source)` (lodash) | 原型链污染 | CWE-1321 |
| `_.set(object, path, value)` | 原型链污染 | CWE-1321 |
| `_.setWith(object, path, value)` | 原型链污染 | CWE-1321 |
| `_.defaultsDeep(object, source)` | 原型链污染 | CWE-1321 |
| `Object.assign(target, source)` | 单层覆盖（相对安全） | - |
| `$.extend(true, target, source)` (jQuery) | 原型链污染 | CWE-1321 |
| `deepMerge(target, source)` 自写 | 原型链污染 | CWE-1321 |

### SQL 注入

| sink | 危险 | CWE |
|---|---|---|
| `db.query("SELECT * FROM x WHERE id = " + userInput)` | 拼接 | CWE-89 |
| `db.query(\`SELECT * FROM x WHERE id = ${userInput}\`)` | 模板字符串 | CWE-89 |
| `sequelize.query("SELECT * FROM x WHERE id = " + userInput)` | 同上 | CWE-89 |
| `Model.findAll({ where: { id: userInput } })` | ORM 参数化（安全） | - |
| `Model.sequelize.query("... " + userInput)` | 拼接 | CWE-89 |

### NoSQL 注入

| sink | 危险 | CWE |
|---|---|---|
| `db.collection.findOne({ username: req.body.username, password: req.body.password })` | 整对象透传 | CWE-943 |
| `db.collection.find({ $where: req.body.q })` | `$where` 注入 | CWE-943 |
| `db.collection.find({ $or: req.body })` | `$or` 注入 | CWE-943 |
| `db.collection.find({ username: req.body.username })` 简单查询 | **安全**（类型固定为 string） | - |

### 命令执行

| sink | 危险 | CWE |
|---|---|---|
| `child_process.exec(userInput)` | 拼接 | CWE-78 |
| `child_process.execSync(\`ls ${userInput}\`)` | 模板字符串 | CWE-78 |
| `child_process.execFile("ls", ["-l", userInput])` | **数组形式安全** | - |
| `child_process.spawn("ls", [userInput])` | 数组形式安全 | - |

### 路径 / 文件

| sink | 危险 | CWE |
|---|---|---|
| `fs.readFile("/data/" + userInput)` | 路径遍历 | CWE-22 |
| `fs.readFileSync(path.join("/data", userInput))` | 路径遍历 | CWE-22 |
| `fs.createReadStream(userInput)` | 路径遍历 | CWE-22 |
| `fs.writeFile("/upload/" + userInput, data)` | 路径写入 | CWE-22 |
| `fs.unlink("/data/" + userInput)` | 任意删除 | CWE-22 |
| `res.sendFile(path.join(publicDir, userInput))` | 路径遍历 | CWE-22 |
| `require(userInput)` | 任意模块加载 | CWE-98 |

### SSRF

| sink | 危险 | CWE |
|---|---|---|
| `fetch(userInput)` | SSRF | CWE-918 |
| `axios.get(userInput)` | SSRF | CWE-918 |
| `axios.post(userInput, data)` | SSRF | CWE-918 |
| `http.get(userInput)` | SSRF | CWE-918 |
| `https.get(userInput)` | SSRF | CWE-918 |
| `got(userInput)` | SSRF | CWE-918 |
| `node-fetch(userInput)` | SSRF | CWE-918 |

### XSS（前端 sink）

| sink | 危险 | CWE |
|---|---|---|
| `element.innerHTML = userInput` | DOM-XSS | CWE-79 |
| `element.outerHTML = userInput` | DOM-XSS | CWE-79 |
| `element.insertAdjacentHTML("beforeend", userInput)` | DOM-XSS | CWE-79 |
| `document.write(userInput)` | DOM-XSS | CWE-79 |
| `document.writeln(userInput)` | DOM-XSS | CWE-79 |
| `$(".x").html(userInput)` | jQuery XSS | CWE-79 |
| `$(".x").append(userInput)` | jQuery XSS | CWE-79 |
| `$(".x").prepend(userInput)` | jQuery XSS | CWE-79 |
| `$(".x").before(userInput)` | jQuery XSS | CWE-79 |
| `$(".x").after(userInput)` | jQuery XSS | CWE-79 |
| `$(".x").replaceWith(userInput)` | jQuery XSS | CWE-79 |
| `element.setAttribute("onclick", userInput)` | XSS (event handler) | CWE-79 |
| `element.setAttribute("href", "javascript:" + userInput)` | javascript: XSS | CWE-79 |
| `location.href = userInput` | Open Redirect / javascript: | CWE-601/CWE-79 |
| `location.assign(userInput)` | 同上 | CWE-601 |
| `location.replace(userInput)` | 同上 | CWE-601 |
| `window.open(userInput)` | Open Redirect | CWE-601 |

### Crypto

| sink | 危险 | CWE |
|---|---|---|
| `crypto.createHash("md5")` | 弱哈希 | CWE-327 |
| `crypto.createHash("sha1")` | 弱哈希 | CWE-327 |
| `crypto.createCipher("des", key)` (Node 旧) | 弱加密 | CWE-327 |
| `crypto.createCipheriv("aes-128-ecb", key, "")` | 弱模式 | CWE-327 |
| `Math.random()` 用于 token / salt | 不安全随机 | CWE-338 |
| `crypto.randomBytes(n)` | **安全** | - |
| `crypto.randomUUID()` | **安全** | - |

### JWT 漏洞

| sink | 危险 | CWE |
|---|---|---|
| `jwt.verify(token, secret, { algorithms: ["none"] })` | alg=none 绕过 | CWE-347 |
| `jwt.verify(token, "secret", { algorithms: ["HS256", "RS256"] })` | 混用算法 → RS256→HS256 攻击 | CWE-347 |
| `jwt.verify(token, "")` | 密钥空 | CWE-798 |
| `jwt.decode(token)` | 仅 decode 不 verify | CWE-347 |
| `jwt.verify(token)` (无 secret) | 不安全 | CWE-347 |

## 5. Go

### 命令执行

| sink | 危险 | CWE |
|---|---|---|
| `exec.Command("sh", "-c", "ls " + userInput).Run()` | 拼接 | CWE-78 |
| `exec.Command("ls", userInput).Run()` | 数组形式（参数化） | CWE-78(需审查) |
| `exec.Command(userInput).Run()` | 完整可控 | CWE-78 |

### 反序列化

| sink | 危险 | CWE |
|---|---|---|
| `gob.NewDecoder(r).Decode(&v)` | gob 反序列化（应用内可控时相对安全） | CWE-502 |
| `json.Unmarshal(userInput, &v)` | 注入结构体字段 | CWE-915 (Mass Assignment) |
| `yaml.Unmarshal(userInput, &v)` (yaml.v2 默认) | YAML 反序列化 | CWE-502 |
| `proto.Unmarshal(userInput, msg)` | protobuf 反序列化 | - |
| `msgpack.Unmarshal(userInput, &v)` | msgpack | - |

### SQL 注入

| sink | 危险 | CWE |
|---|---|---|
| `db.Query("SELECT * FROM x WHERE id = " + userInput)` | 拼接 | CWE-89 |
| `db.Query("SELECT * FROM x WHERE id = $1", userInput)` | **参数化安全** | - |
| `db.Exec(fmt.Sprintf("INSERT ... %s", userInput))` | 拼接 | CWE-89 |
| GORM `db.Where("name = ?", userInput).Find(&users)` | 参数化 | - |
| GORM `db.Where(fmt.Sprintf("name = '%s'", userInput)).Find(&users)` | 拼接 | CWE-89 |

### SSRF

| sink | 危险 | CWE |
|---|---|---|
| `http.Get(userInput)` | SSRF | CWE-918 |
| `http.NewRequest("GET", userInput, nil)` | SSRF | CWE-918 |
| `http.Post(userInput, "application/json", body)` | SSRF | CWE-918 |
| `http.Client.Do(req)` (URL 可控) | SSRF | CWE-918 |

### 路径

| sink | 危险 | CWE |
|---|---|---|
| `os.Open("/data/" + userInput)` | 路径遍历 | CWE-22 |
| `os.OpenFile("/upload/" + userInput, ...)` | 路径写入 | CWE-22 |
| `os.ReadFile("/data/" + userInput)` | 路径读取 | CWE-22 |
| `ioutil.ReadFile("/data/" + userInput)` | 同上 | CWE-22 |
| `filepath.Join("/data", userInput)` | 路径遍历 | CWE-22 |

### XSS（服务端 + html/template）

| sink | 危险 | CWE |
|---|---|---|
| `template.HTML(userInput)` | XSS | CWE-79 |
| `template.HTMLAttr(userInput)` | XSS (attr) | CWE-79 |
| `template.JS(userInput)` | XSS (JS context) | CWE-79 |
| `template.URL(userInput)` | URL injection | CWE-79 |
| `template.JSStr(userInput)` | XSS | CWE-79 |

### 加密

| sink | 危险 | CWE |
|---|---|---|
| `md5.Sum([]byte(password))` | 弱哈希 | CWE-327 |
| `sha1.Sum([]byte(password))` | 弱哈希 | CWE-327 |
| `des.NewCipher(key)` | 弱加密 | CWE-327 |
| `rand.Int(rand.Reader, big.NewInt(100))` | **安全** | - |
| `math/rand.Intn(n)` | 不安全随机 | CWE-338 |

## 6. Ruby

### RCE / eval

| sink | 危险 | CWE |
|---|---|---|
| `eval(userInput)` | RCE | CWE-94 |
| `eval("code " + userInput)` | RCE | CWE-94 |
| `instance_eval(userInput)` | RCE | CWE-94 |
| `class_eval(userInput)` | RCE | CWE-94 |
| `module_eval(userInput)` | RCE | CWE-94 |
| `send(userInput, *args)` | 任意方法调用 | CWE-94 |
| `public_send(userInput, *args)` | 同上 | CWE-94 |
| `method(userInput).call` | 同上 | CWE-94 |

### 命令执行

| sink | 危险 | CWE |
|---|---|---|
| `system(userInput)` | RCE | CWE-78 |
| `system("ls #{userInput}")` | 字符串插值 | CWE-78 |
| `exec(userInput)` | RCE | CWE-78 |
| `\`ls #{userInput}\`` (反引号) | RCE | CWE-78 |
| `%x(ls #{userInput})` | RCE | CWE-78 |
| `spawn(userInput)` | RCE | CWE-78 |
| `open("\| ls #{userInput}")` | 管道 | CWE-78 |
| `IO.popen("ls #{userInput}")` | 管道 | CWE-78 |
| `Process.spawn(userInput)` | RCE | CWE-78 |
| `Kernel.open(userInput)` | RCE (管道路由) | CWE-78 |

### 反序列化

| sink | 危险 | CWE |
|---|---|---|
| `YAML.load(userInput)` | YAML 反序列化 | CWE-502 |
| `YAML.load(userInput, permitted_classes: [...])` | 部分白名单仍可能 RCE | CWE-502 |
| `YAML.safe_load(userInput)` | **安全** | - |
| `YAML.unsafe_load(userInput)` | 危险 | CWE-502 |
| `Marshal.load(userInput)` | Marshal 反序列化 | CWE-502 |
| `Marshal.restore(userInput)` | 同上 | CWE-502 |
| `Oj.load(userInput, mode: :object)` | JSON → Object 转换（注意反序列化） | CWE-502 |
| `JSON.parse(userInput)` | **安全**（不实例化） | - |

### SQL 注入

| sink | 危险 | CWE |
|---|---|---|
| `User.where("name = '#{params[:name]}'")` | 字符串插值 | CWE-89 |
| `User.where("name = ?", params[:name])` | **安全** | - |
| `ActiveRecord::Base.connection.execute("... " + params[:x])` | 拼接 | CWE-89 |
| `Model.find_by_sql("... " + params[:x])` | 拼接 | CWE-89 |
| `sanitize_sql_array(["... #{params[:x]}", ...])` | 拼接 | CWE-89 |

### SSTI

| sink | 危险 | CWE |
|---|---|---|
| `ERB.new("Hello <%= #{userInput} %>").result` | ERB 注入 | CWE-94 |
| `Tilt::ERBTemplate.new { userInput }.render` | 同上 | CWE-94 |
| `Haml::Engine.new(userInput).render` | Haml SSTI | CWE-94 |
| `Slim::Template.new(userInput).render` | Slim SSTI | CWE-94 |

### 路径 / 文件

| sink | 危险 | CWE |
|---|---|---|
| `File.open("/data/" + userInput)` | 路径遍历 | CWE-22 |
| `File.read("/data/" + userInput)` | 路径遍历 | CWE-22 |
| `File.write("/upload/" + userInput, data)` | 路径写入 | CWE-22 |
| `File.unlink("/data/" + userInput)` | 任意删除 | CWE-22 |
| `FileUtils.rm_rf("/data/" + userInput)` | 任意删除 | CWE-22 |

### 加密

| sink | 危险 | CWE |
|---|---|---|
| `Digest::MD5.hexdigest(password)` | 弱哈希 | CWE-327 |
| `Digest::SHA1.hexdigest(password)` | 弱哈希 | CWE-327 |
| `BCrypt::Password.create(password)` | **安全** | - |
| `OpenSSL::Cipher::DES.new` | 弱加密 | CWE-327 |
| `Random.rand(n)` 用于 token | 不安全随机 | CWE-338 |
| `SecureRandom.hex(n)` | **安全** | - |
| `SecureRandom.uuid` | **安全** | - |

## 7. C# / .NET

### RCE / eval

| sink | 危险 | CWE |
|---|---|---|
| `System.Diagnostics.Process.Start("cmd.exe", "/c " + userInput)` | RCE | CWE-78 |
| `Process.Start(new ProcessStartInfo("cmd", "/c " + userInput))` | RCE | CWE-78 |
| `new ProcessStartInfo(userInput)` | RCE | CWE-78 |
| `Microsoft.JScript.Eval.JScriptEvaluate(...)` | 旧 ASP.NET eval | CWE-94 |
| `Type.GetType(userInput).GetMethod(...).Invoke(...)` | 反射 RCE | CWE-94 |

### 反序列化

| sink | 危险 | CWE |
|---|---|---|
| `new BinaryFormatter().Deserialize(stream)` | 反序列化 RCE | CWE-502 |
| `new ObjectStateFormatter().Deserialize(stream)` | 同上 | CWE-502 |
| `new LosFormatter().Deserialize(stream)` | 同上 | CWE-502 |
| `new NetDataContractSerializer().ReadObject(stream)` | 同上 | CWE-502 |
| `new DataContractJsonSerializer(typeof(object)).ReadObject(stream)` | 同上 | CWE-502 |
| `JsonConvert.DeserializeObject<object>(json)` (Newtonsoft) | Mass Assignment | CWE-915 |
| `JavaScriptSerializer().Deserialize<object>(json)` | 反序列化 | CWE-502 |
| `SoapFormatter().Deserialize(stream)` | SOAP 反序列化 | CWE-502 |

### SQL 注入

| sink | 危险 | CWE |
|---|---|---|
| `new SqlCommand("SELECT * FROM x WHERE id = " + userInput)` | 拼接 | CWE-89 |
| `new SqlCommand($"SELECT * FROM x WHERE id = {userInput}")` | 字符串插值 | CWE-89 |
| `dbContext.Users.FromSqlRaw("... " + userInput)` | EF Core 拼接 | CWE-89 |
| `dbContext.Users.FromSqlInterpolated($"... {userInput}")` | **参数化** | - |
| `dbContext.Database.ExecuteSqlRaw("... " + userInput)` | EF Core 拼接 | CWE-89 |
| `SqlCommand.Parameters.AddWithValue(...)` 配预编译 | **安全** | - |

### XXE

| sink | 危险 | CWE |
|---|---|---|
| `XmlDocument.Load(userInput)` 未禁用 DTD | XXE | CWE-611 |
| `XmlReader.Create(userInput)` 未配置 | XXE | CWE-611 |
| `XDocument.Load(userInput)` | XXE | CWE-611 |
| `XmlSerializer.Deserialize(stream)` | 一般安全 | - |

### SSRF

| sink | 危险 | CWE |
|---|---|---|
| `new HttpClient().GetAsync(userInput)` | SSRF | CWE-918 |
| `new WebClient().DownloadString(userInput)` | SSRF | CWE-918 |
| `new WebRequest.Create(userInput)` | SSRF | CWE-918 |
| `HttpClient.GetStringAsync(userInput)` | SSRF | CWE-918 |

### 路径 / 文件

| sink | 危险 | CWE |
|---|---|---|
| `File.ReadAllText("/data/" + userInput)` | 路径遍历 | CWE-22 |
| `File.WriteAllText("/upload/" + userInput, data)` | 路径写入 | CWE-22 |
| `File.Delete("/data/" + userInput)` | 任意删除 | CWE-22 |
| `new FileInfo("/data/" + userInput)` | 路径遍历 | CWE-22 |
| `Path.Combine("/data", userInput)` | 路径遍历（不防护 ../） | CWE-22 |

### XSS (Razor)

| sink | 危险 | CWE |
|---|---|---|
| `@Html.Raw(userInput)` | XSS | CWE-79 |
| `HtmlString` 包装 userInput | XSS | CWE-79 |
| `<div>@userInput</div>` | **安全** (Razor 自动转义) | - |
| `<%= userInput %>` (WebForm) | XSS | CWE-79 |
| `Response.Write(userInput)` | XSS | CWE-79 |

### Crypto

| sink | 危险 | CWE |
|---|---|---|
| `MD5.Create()` | 弱哈希 | CWE-327 |
| `SHA1.Create()` | 弱哈希 | CWE-327 |
| `DESCryptoServiceProvider` | 弱加密 | CWE-327 |
| `new Random()` 用于 token | 不安全随机 | CWE-338 |
| `RandomNumberGenerator.Create()` | **安全** | - |
| `Rfc2898DeriveBytes` | **安全** (PBKDF2) | - |
| `BCrypt.Net.BCrypt.HashPassword(...)` | **安全** | - |

### LDAP 注入

| sink | 危险 | CWE |
|---|---|---|
| `new DirectoryEntry("LDAP://..." + userInput)` | LDAP 注入 | CWE-90 |
| `DirectorySearcher.Filter = "(uid=" + userInput + ")"` | LDAP 注入 | CWE-90 |
| `PrincipalContext.FindByIdentity(userInput)` | 风险（但 framework 内部一般安全） | CWE-90 |

### 硬编码

| sink | 危险 | CWE |
|---|---|---|
| `ConfigurationManager.AppSettings["password"]` 在源码写死 | 硬编码 | CWE-798 |
| `string connectionString = "Server=...;Password=..."` | 硬编码 | CWE-798 |

## 8. 跨语言共性危险

| 类别 | 模式 | 风险 |
|---|---|---|
| 注释含 TODO / FIXME / 临时代码 | 注释 | 信息泄露 |
| commit 提交记录 | `.git/` 暴露 | 密钥 |
| `.env` 提交进仓库 | 密钥泄露 | CWE-798 |
| `application.properties` 提交进仓库 | DB 密码 | CWE-798 |
| `web.config` 提交 | DB 连接串 | CWE-798 |
| 错误页含详细堆栈 | 生产环境 | CWE-209 |
| 注释中的真实凭据 | 信息泄露 | CWE-798 |
| README 中含默认凭据 | 提示 | CWE-798 |
| 调试接口 / 注释的"v2.0 删掉" | 危险 | CWE-489 |
