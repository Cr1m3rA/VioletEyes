# 危险配置速查

> Agent 在 Phase 4 阶段读 manifest / 配置文件时查阅。

## 1. 框架默认不安全配置

### 1.1 Java Spring Boot

| 配置 | 文件 | 风险 | 修复 |
|---|---|---|---|
| `debug=true` | application.yml | 暴露自动配置报告 | 生产关闭 |
| `spring.main.banner-mode=off` 不影响安全 | - | - | - |
| `spring.devtools.restart.enabled=true` 生产开启 | application.yml | 远程重启 RCE | 生产关闭 |
| `management.endpoints.web.exposure.include=*` | application.yml | 暴露所有 actuator | 仅 expose 必要 |
| `management.endpoint.env.enabled=true` | application.yml | 暴露环境变量 / 密钥 | 关闭 |
| `management.endpoint.health.show-details=always` | application.yml | 暴露详细信息 | 设为 `when_authorized` |
| `server.error.include-stacktrace=always` | application.yml | 暴露堆栈 | 设为 `never` |
| `server.error.include-message=always` | application.yml | 暴露错误信息 | 设为 `never` |
| `logging.level.org.springframework.web=DEBUG` | application.yml | 记录请求详情 | 生产 INFO |
| `server.servlet.session.cookie.secure=false` | application.yml | cookie 嗅探 | 设为 true |
| `server.servlet.session.cookie.http-only=false` | application.yml | XSS 可窃取 | 设为 true |
| `server.servlet.session.cookie.same-site=` | application.yml | CSRF | 设为 `lax` 或 `strict` |

### 1.2 Spring Security

| 配置 | 风险 | 修复 |
|---|---|---|
| `.csrf().disable()` | CSRF 关闭 | 启用（API 场景可改用 token 鉴权） |
| `.formLogin().permitAll()` | 任意访问 | 限制 |
| `.authorizeRequests().anyRequest().permitAll()` | 全部公开 | 显式 deny |
| `.addFilterBefore(..., DisableEncodeUrlFilter.class)` 缺失 | Session fixation | 启用 |
| 密码未 bcrypt 哈希 | 弱密码 | BCrypt + strength>=10 |
| `httpBasic()` 无 HTTPS | 中间人 | 仅 HTTPS |
| `headers().disable()` | 缺失安全头 | 启用 |
| `cors().and().csrf().disable()` | CORS+CSRF 关闭 | 至少 CORS 白名单 |
| `frameOptions().disable()` | Clickjacking | 启用 DENY |

### 1.3 Django

| 配置 | 风险 | 修复 |
|---|---|---|
| `DEBUG = True` | 暴露堆栈 / 设置 | 生产 False |
| `SECRET_KEY = 'xxx'` 写死 | Session 伪造 | 环境变量 + 定期轮换 |
| `ALLOWED_HOSTS = ['*']` | Host header injection | 显式列表 |
| `SECURE_SSL_REDIRECT = False` | HTTP 明文 | True（生产） |
| `SESSION_COOKIE_SECURE = False` | cookie 嗅探 | True |
| `SESSION_COOKIE_HTTPONLY = False` | XSS 窃取 session | True |
| `CSRF_COOKIE_SECURE = False` | 同上 | True |
| `CSRF_COOKIE_HTTPONLY = False` | 同上 | True |
| `CORS_ALLOW_ALL_ORIGINS = True` | CORS 全开 | 显式白名单 |
| `CORS_ALLOW_CREDENTIALS = True` + `*` | 危险组合 | 限定 origin |
| `MIDDLEWARE` 缺失 `SecurityMiddleware` | 缺失安全头 | 添加 |
| `MIDDLEWARE` 缺失 `CsrfViewMiddleware` | CSRF 关闭 | 添加（API 场景用 token） |
| `MIDDLEWARE` 缺失 `SessionMiddleware` (可能) | session 异常 | 检查 |
| `AUTH_PASSWORD_VALIDATORS = []` | 弱密码 | 添加 |
| `PASSWORD_HASHERS = ['MD5PasswordHasher']` | 弱哈希 | 使用 Argon2 / BCrypt |
| `DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440` (默认 2.5MB) | 限制 OK | 但需检查下游 |
| `FILE_UPLOAD_PERMISSIONS = 0o644` (默认) | 文件可读 | 0o600 |
| `DEFAULT_FROM_EMAIL = ''` | 邮件伪造 | 显式 |

### 1.4 Flask

| 配置 | 风险 | 修复 |
|---|---|---|
| `app.run(debug=True)` | 远程控制台 (Werkzeug PIN) | 生产用 gunicorn |
| `SECRET_KEY = 'xxx'` 写死 | Session 伪造 | 环境变量 |
| `SESSION_COOKIE_SECURE = False` | 嗅探 | True |
| `SESSION_COOKIE_HTTPONLY = False` | XSS | True |
| `SESSION_COOKIE_SAMESITE = None` | CSRF | 'Lax' 或 'Strict' |
| `PERMANENT_SESSION_LIFETIME = 31 * 24 * 3600` (默认) | Session 过长 | 缩短 |
| `WTF_CSRF_ENABLED = False` | CSRF 关闭 | True |
| `TEMPLATES_AUTO_RELOAD = True` 生产 | 信息泄露 | False |
| `TRAP_HTTP_EXCEPTIONS = False` | 自定义 500 | True |
| `TRAP_BAD_REQUEST_ERRORS = True` | 隐藏 400 | 视场景 |
| `JSON_AS_ASCII = True` | 字符编码 OK | - |
| `JSONIFY_PRETTYPRINT_REGULAR = True` 生产 | 信息泄露 | False |

### 1.5 FastAPI

| 配置 | 风险 | 修复 |
|---|---|---|
| `debug=True` (uvicorn) | 远程控制台 | False |
| `reload=True` 生产 | 远程重启 | False |
| `--host 0.0.0.0` | 公网暴露 | 绑定 127.0.0.1 / 内网 |
| `allow_origins=["*"]` (CORS) | CORS 全开 | 显式白名单 |
| `allow_credentials=True` + `*` | 危险组合 | 限定 |
| `https_only=False` cookie | 嗅探 | True |
| `samesite="lax"` (默认) | CSRF 部分 | strict 视场景 |

### 1.6 Node.js / Express

| 配置 | 风险 | 修复 |
|---|---|---|
| `app.use(cors())` 无配置 | CORS 全开 | `cors({origin: [...]})` |
| `app.use(helmet())` 缺失 | 缺失安全头 | 添加 |
| `app.use(express.static('public'))` 含 `..` | 路径遍历 | 静态资源目录独立 |
| `express-session` cookie.secure=false | 嗅探 | true |
| `express-session` cookie.httpOnly=false | XSS | true |
| `express-session` secret='xxx' 写死 | Session 伪造 | 环境变量 |
| `express.json({limit: '50mb'})` | DoS | 限制 |
| `express.urlencoded({extended: true, limit: '50mb'})` | 同上 | 限制 |
| `req.body` 透传到 DB query | 注入 | 用 ORM / 参数化 |
| `process.env` 中密钥 | 提交风险 | 加密仓库 |
| `morgan('combined')` 生产 | 日志 PII | 精简 |
| `cookie-parser` + 自写解析 | 风险 | 用 secure cookie 库 |
| `app.set('trust proxy', true)` + 任意 X-Forwarded-For | IP 伪造 | 限定代理层数 |
| `csrf()` 中间件缺失 | CSRF | 添加（API 用 token） |
| `express-rate-limit` 缺失 | DoS / 爆破 | 添加 |
| `body-parser` raw 解析 | 字节流解析 | 仅必要场景 |

### 1.7 PHP

| 配置 | 风险 | 修复 |
|---|---|---|
| `display_errors = On` | 信息泄露 | Off |
| `display_startup_errors = On` | 信息泄露 | Off |
| `expose_php = On` | 版本泄露 | Off |
| `allow_url_fopen = On` | SSRF (file_get_contents) | Off |
| `allow_url_include = On` | RFI | Off |
| `error_reporting = E_ALL` 生产 | 错误详情 | 静默 + 自写 logger |
| `session.cookie_secure = 0` | 嗅探 | 1 |
| `session.cookie_httponly = 0` | XSS | 1 |
| `session.cookie_samesite = "Lax"` (PHP 7.3+) | CSRF | Strict |
| `session.use_strict_mode = 0` | Session 固定 | 1 |
| `session.use_only_cookies = 0` | URL session | 1 |
| `session.gc_maxlifetime` 过长 | 长期有效 | 缩短 |
| `upload_max_filesize` 过大 | DoS | 限制 |
| `post_max_size` 过大 | DoS | 限制 |
| `open_basedir` 未设 | 任意文件 | 设置 |
| `disable_functions` 缺失 | 任意命令 | 限制 |

### 1.8 Laravel

| 配置 (.env) | 风险 | 修复 |
|---|---|---|
| `APP_DEBUG=true` | 暴露设置 / 堆栈 | False |
| `APP_KEY=` 空 | 加密失效 | 32 字符随机 |
| `APP_ENV=local` | 暴露详细错误 | production |
| `APP_URL=http://` | 混合内容 | https |
| `DB_PASSWORD=` 提交 | 密钥泄露 | 环境变量 |
| `MAIL_PASSWORD=` 提交 | 同上 | 同上 |
| `AWS_SECRET_ACCESS_KEY=` 提交 | 云密钥 | 轮换 + 环境变量 |
| `SESSION_DRIVER=cookie` | 客户端 session | 改 database/redis |
| `SESSION_DOMAIN` 含 `.com` | 跨子域共享 | 限定 |
| `SESSION_SECURE_COOKIE=false` | 嗅探 | true |
| `SESSION_HTTP_ONLY=false` | XSS | true |
| `SESSION_SAME_SITE=lax` | CSRF | strict |
| `SANCTUM_STATEFUL_DOMAINS=*` | 跨站 session | 限定 |
| `CORS_ALLOWED_ORIGINS=*` | CORS 全开 | 限定 |
| `TRUSTED_PROXIES=*` | IP 伪造 | 限定 |
| `HASH_ROUNDS=4` | 弱哈希 | >=10 |

### 1.9 Go

| 配置 | 风险 | 修复 |
|---|---|---|
| `gin.SetMode(gin.DebugMode)` 生产 | 详细信息 | ReleaseMode |
| `gin.Default()` (含 logger) 生产 | 日志 PII | 自定义 logger |
| `r.Use(cors.Default())` | CORS 全开 | 限定 |
| `r.Use(cors.AllowAll())` | 同上 | 限定 |
| 绑定 `0.0.0.0:8080` | 公网暴露 | 127.0.0.1 |
| `c.Request.URL.ParseForm()` 后拼接 | 注入风险 | 用 c.Query / c.DefaultQuery |
| Echo / Fiber 同理 | - | - |

### 1.10 Ruby Rails

| 配置 | 风险 | 修复 |
|---|---|---|
| `config.consider_all_requests_local = true` (默认 dev) | 详细错误 | production=false |
| `config.action_dispatch.show_exceptions = true` (默认 dev) | 详细错误 | production=false |
| `config.action_controller.allow_forgery_protection = false` | CSRF 关闭 | true |
| `config.force_ssl = false` | HTTP | true |
| `config.session_store :cookie_store, key: '...'` | Session 在客户端 | 改 server-side |
| `config.secret_key_base` 写死 | 密钥泄露 | 环境变量 |
| `config.web_console.whitelisted_ips` 公网 | 控制台 | 限定 |
| `config.web_console.permissions = '0.0.0.0/0'` | 同上 | 限定 |
| `config.hosts` 含 `[]` (允许任意 host) | Host header | 限定 |
| `config.cors_allowed_origins = '*'` | CORS 全开 | 限定 |

### 1.11 C# / .NET

| 配置 | 风险 | 修复 |
|---|---|---|
| `<customErrors mode="Off"/>` | 详细错误 | RemoteOnly / On |
| `<compilation debug="true"/>` 生产 | 详细错误 + 性能 | false |
| `<httpCookies requireSSL="false"/>` | 嗅探 | true |
| `<httpCookies httpOnlyCookies="false"/>` | XSS | true |
| `enableHeaderChecking="false"` | Header 注入 | true |
| `<sessionState cookieless="true"/>` | URL session | false |
| `<sessionState cookieSameSite="Lax"/>` | CSRF | Strict |
| `services.AddCors(options => ...)` 全开 | CORS | 限定 |
| `services.AddControllers().AddNewtonsoftJson()` + `TypeNameHandling.Auto` | 反序列化 RCE | 设为 None |
| `app.UseHsts()` 缺失 | 缺 HSTS | 启用 |
| `app.UseHttpsRedirection()` 缺失 | HTTP 流量 | 启用 |
| `app.UseExceptionHandler("/error")` 缺失 | 错误详情 | 启用 |
| `AntiForgery` 缺失 | CSRF | 启用 |
| `[AllowAnonymous]` 滥用 | 越权 | 审查每个 |

## 2. 危险 .env / 配置文件字段

下列字段在仓库内出现 → 警告（不直接升 finding，需 LLM 判断）：

```
DATABASE_URL=...
DB_HOST=... / DB_USER=... / DB_PASSWORD=...
REDIS_URL=...
RABBITMQ_URL=...
MONGODB_URI=...
ELASTICSEARCH_URL=...
KAFKA_BROKERS=...

# 认证
JWT_SECRET=...
SESSION_SECRET=...
COOKIE_SECRET=...
CSRF_SECRET=...
ENCRYPTION_KEY=...
SIGNING_KEY=...

# 云
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
GCP_SERVICE_ACCOUNT=...
AZURE_CLIENT_SECRET=...

# 第三方 API
SENDGRID_API_KEY=...
MAILGUN_API_KEY=...
TWILIO_AUTH_TOKEN=...
STRIPE_SECRET_KEY=...
PAYPAL_CLIENT_SECRET=...
SLACK_WEBHOOK_URL=...
GITHUB_TOKEN=...
GITLAB_TOKEN=...
HEROKU_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
HUGGINGFACE_TOKEN=...

# 邮件
SMTP_HOST=... / SMTP_PORT=... / SMTP_USER=... / SMTP_PASSWORD=...

# 其他
PRIVATE_KEY=... (RSA / SSH)
RSA_PRIVATE_KEY=...
SSH_PRIVATE_KEY=...
TOKEN=... / API_KEY=... / SECRET=...
```

## 3. 危险 manifest 字段

| 字段 | 含义 | 风险 |
|---|---|---|
| `package.json` 的 `scripts.preinstall: "curl ... \| bash"` | 远程脚本 | 供应链 |
| `package.json` 的 `postinstall: "..."` | 同上 | 供应链 |
| `Gemfile` 的 `source: 'https://...'` 非官方 | 不安全源 | 供应链 |
| `requirements.txt` 含 `--extra-index-url` | 第三方源 | 供应链 |
| `composer.json` 的 `repositories` 含非官方 | 第三方源 | 供应链 |
| `pom.xml` 的 `<repository>` 非官方 | 第三方源 | 供应链 |
| `*.gemspec` 引用 git 协议 | MITM 风险 | 供应链 |

## 4. 危险的文件 / 路径

| 路径 | 含义 | 风险 |
|---|---|---|
| `.env` / `.env.local` / `.env.production` | 环境配置 | 密钥 |
| `application.properties` 含密码 | Java 配置 | 密钥 |
| `application.yml` 含密码 | Java 配置 | 密钥 |
| `web.config` 含 `connectionString` | .NET 配置 | 密钥 |
| `appsettings.json` 含连接串 | .NET 配置 | 密钥 |
| `database.yml` (Rails) | DB 配置 | 密钥 |
| `secrets.yml` (Rails) | 密钥 | 密钥 |
| `config.json` / `settings.json` 含 token | 通用 | 密钥 |
| `id_rsa` / `id_rsa.pub` | SSH 私钥 | 密钥 |
| `*.pem` / `*.key` | 私钥 | 密钥 |
| `.npmrc` 含 `_authToken` | npm 凭据 | 密钥 |
| `.pypirc` 含 password | PyPI 凭据 | 密钥 |
| `~/.aws/credentials` | AWS 凭据 | 密钥 |
| `service-account.json` | GCP 凭据 | 密钥 |

Agent 读这些文件不直接报告内容，但需标记"配置文件含密钥字段"，提醒用户加入 .gitignore / 移到 secrets manager。

## 5. 危险的 CI/CD 配置

| 路径 | 风险 |
|---|---|
| `.github/workflows/*.yml` 拉取 PR 代码后跑 PR 提供者的代码 | 供应链 |
| GitHub Actions `pull_request_target` 触发且 checkout PR | 供应链 |
| GitLab CI 任意 tag 触发 | 供应链 |
| Jenkinsfile 拉取外部脚本 | 供应链 |
| `.travis.yml` 含密钥 | 密钥泄露（公开仓库） |
| `.gitlab-ci.yml` 含密钥 | 同上 |

## 6. 注释中的危险信号

| 模式 | 风险 |
|---|---|
| `// TODO: add auth` | 未鉴权 |
| `// FIXME: SQL injection` | 已注入 |
| `// HACK: bypass for xxx` | 不安全 bypass |
| `// XXX: this is a backdoor for xxx` | 后门 |
| `// TEMP: remove before production` | 临时代码遗留 |
| `// admin:admin` 等注释凭据 | 凭据泄露 |
| `// password = "xxx"` | 硬编码 |
| `// internal IP: 10.x.x.x` | 内部信息 |
| `// @deprecated since 1.2.3 - use safeQuery()` | 仍存在 |

## 7. 危险模板 / 前端配置

| 配置 | 风险 | 修复 |
|---|---|---|
| CSP `unsafe-inline` | XSS | 删除 |
| CSP `unsafe-eval` | XSS | 删除 |
| CSP `*` (default-src) | XSS | 限定 |
| `X-Frame-Options: ALLOWALL` | Clickjacking | DENY / SAMEORIGIN |
| `Access-Control-Allow-Origin: *` | CORS | 限定 |
| `Access-Control-Allow-Credentials: true` + `*` | 危险 | 限定 |
| `Strict-Transport-Security` 缺失 | 缺 HSTS | 启用 |
| `X-Content-Type-Options: nosniff` 缺失 | MIME 嗅探 | 启用 |
| `Referrer-Policy: unsafe-url` | 信息泄露 | strict-origin |
| `Permissions-Policy: *` | 浏览器 API 全开 | 限定 |
| `<meta http-equiv="Content-Security-Policy" content="...">` 缺 | 缺 CSP | 添加 |
| `target="_blank"` 无 `rel="noopener"` | Tabnabbing | 加 noopener |

## 8. 危险服务监听配置

| 模式 | 风险 |
|---|---|
| `app.listen(0.0.0.0, port)` | 公网监听 |
| `server.bind("0.0.0.0", port)` | 同上 |
| `http.ListenAndServe(":80", nil)` | 同上 |
| `app.run(host="0.0.0.0", port=80)` | 同上 |
| `app.config['SERVER_NAME'] = '0.0.0.0'` | 同上 |
| `--host 0.0.0.0` (uvicorn) | 同上 |
| Werkzeug `app.run(host='0.0.0.0')` | 同上 + Debug PIN |
| Flask `--host 0.0.0.0` | 同上 |
| Vite `server.host = '0.0.0.0'` | 同上（前端） |
| DevServer `host: '0.0.0.0'` (webpack) | 同上 |
| 内嵌 H2 Console (Spring) | 暴露数据库 |
| Spring Boot DevTools | 远程重启 |
| Django `runserver 0.0.0.0:8000` | 同上 + Debug |
| PHP built-in server `php -S 0.0.0.0:8000` | 同上 |

Agent 看到这些配置 → 提醒绑定 127.0.0.1 或内网 IP。
