# 危险默认值

> 各框架在"开箱即用"时的不安全默认配置。
> Agent 审计时优先检查。

## 1. Java Spring

### Spring Boot

| 默认 | 风险 | 修复 |
|---|---|---|
| `actuator` 暴露 `/health`, `/info` | 探活 / 信息泄露 | 仅 expose 必要 |
| `error.whitelabel.enabled=true` | Whitelabel 错误页暴露堆栈 | 设为 false + 自定义 |
| `spring.main.banner-mode=console` | 暴露 Spring 版本 | 设为 off |
| `server.tomcat.max-http-form-post-size=2MB` | 默认较小（OK） | - |
| Tomcat 默认监听 8080 | 内部端口 | 改 127.0.0.1 |
| `spring.jackson.default-property-inclusion=ALWAYS` | 序列化 null（可能泄露） | 设为 NON_NULL |
| `spring.jpa.show-sql=true` (dev) | 暴露 SQL | 生产 false |
| `spring.jpa.hibernate.ddl-auto=create-drop` (dev) | 生产将清库 | validate / none |

### Spring Security

| 默认 | 风险 | 修复 |
|---|---|---|
| 无 `spring-boot-starter-security` → 无防护 | 公开所有端点 | 必须显式加 |
| 默认 `BCrypt` 密码编码 | OK | - |
| CSRF 默认开启（form-login） | OK | - |
| `headers().defaultsDisabled` | 缺失安全头 | 启用 |

### MyBatis-Plus

| 默认 | 风险 | 修复 |
|---|---|---|
| 分页插件无 count SQL 优化 | 性能 | 加 PaginationInnerInterceptor |
| 字段策略 `NOT_NULL` | OK | - |
| `WHERE id = #{id}` 默认参数化 | OK | - |
| `LIKE` 拼接 `%${x}%` | SQLi | `LIKE CONCAT('%', #{x}, '%')` |

### Hibernate / JPA

| 默认 | 风险 | 修复 |
|---|---|---|
| `ddl-auto=create` (dev) | 生产将清库 | validate / none |
| `format_sql=true` (dev) | 暴露 SQL | 生产 false |
| `show_sql=true` (dev) | 同上 | 生产 false |

### Tomcat / Jetty

| 默认 | 风险 | 修复 |
|---|---|---|
| Cookie 无 `Secure` flag | 嗅探 | `cookie.setSecure(true)` |
| Cookie 无 `HttpOnly` | XSS 窃取 | `cookie.setHttpOnly(true)` |
| 接受 `TRACE` / `OPTIONS` | 反射 XSS | 禁用 |
| `server.error.include-stacktrace=never` (Spring Boot 2.3+) | OK | - |

## 2. Python

### Django

| 默认 | 风险 | 修复 |
|---|---|---|
| `DEBUG = True` (dev) | 信息泄露 | 生产 False |
| `SECRET_KEY = 'django-insecure-...'` | 已知弱密钥 | 环境变量 + 长随机 |
| `ALLOWED_HOSTS = []` | 拒所有 | 显式列表 |
| `MIDDLEWARE` 默认含 SecurityMiddleware | OK | - |
| 默认 CSRF 中间件开启 | OK | - |
| `STATIC_URL = '/static/'` | 公开 | OK |
| `MEDIA_URL = '/media/'` + MEDIA_ROOT | 公开上传文件 | 谨慎配置 |
| `SESSION_COOKIE_SECURE = False` | 嗅探 | True |
| `PASSWORD_HASHERS[0] = 'PBKDF2PasswordHasher'` | OK | 推荐 Argon2 |
| `AUTH_PASSWORD_VALIDATORS` 默认 4 个 | OK | - |
| `DATA_UPLOAD_MAX_MEMORY_SIZE = 2.5MB` | 默认（OK） | - |
| `FILE_UPLOAD_PERMISSIONS = 0o644` | 文件可读 | 0o600 |
| `USE_TZ = False` | 时区问题 | True |

### Flask

| 默认 | 风险 | 修复 |
|---|---|---|
| `SECRET_KEY = None` | 启动会警告，生产报错 | 必填 |
| `SESSION_COOKIE_SECURE = False` | 嗅探 | True |
| `SESSION_COOKIE_HTTPONLY = True` | OK | - |
| `SESSION_COOKIE_SAMESITE = 'Lax'` | 部分 CSRF 防护 | Strict |
| `WTF_CSRF_ENABLED = True` (flask-wtf) | OK | - |
| `MAX_CONTENT_LENGTH = None` | 无限上传 | 限制 |
| `app.run(debug=True)` (dev) | 远程控制台 | 生产 gunicorn |
| `TEMPLATES_AUTO_RELOAD = None` (prod=false) | OK | - |
| `JSON_SORT_KEYS = True` | 排序（OK） | - |
| `EXPLAIN_TEMPLATE_LOADING = False` | OK | - |

### FastAPI

| 默认 | 风险 | 修复 |
|---|---|---|
| `debug=False` | OK | - |
| CORS 默认 **关闭** | OK | 显式开启 |
| 路径参数无校验 | 注入 | 用 Pydantic / Path() |
| `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")` | OK | - |
| `response_model` 默认 None | 不校验输出 | 显式 |
| 依赖注入默认安全 | OK | - |

## 3. PHP

### PHP 本身

| 默认（php.ini） | 风险 | 修复 |
|---|---|---|
| `display_errors = On` (dev) | 信息泄露 | Off |
| `display_startup_errors = On` | 同上 | Off |
| `expose_php = On` | 版本泄露 | Off |
| `allow_url_fopen = On` | SSRF / RFI | Off（如果不需要） |
| `allow_url_include = Off` | OK | 保持 |
| `error_reporting = E_ALL` | OK（生产配合 display_errors=Off） | - |
| `session.cookie_secure = 0` | 嗅探 | 1 |
| `session.cookie_httponly = 0` | XSS | 1 |
| `session.cookie_samesite = ""` | CSRF | "Lax" 或 "Strict" |
| `session.use_strict_mode = 0` | Session 固定 | 1 |
| `session.use_only_cookies = 1` | OK | 1 |
| `upload_max_filesize = 2M` | 默认（OK） | - |
| `post_max_size = 8M` | 默认（OK） | - |
| `memory_limit = 128M` | OK | - |
| `max_execution_time = 30` | OK | - |
| `open_basedir = ""` | 任意文件 | 设置 |

### Laravel

| 默认 (.env) | 风险 | 修复 |
|---|---|---|
| `APP_ENV=local` | 详细错误 | production |
| `APP_DEBUG=true` (local) | 信息泄露 | false |
| `APP_KEY=` 32 字符 | 必须 | 32 字符 |
| `APP_URL=http://localhost` | HTTP | https://... |
| `LOG_CHANNEL=stack` | OK | - |
| `DB_CONNECTION=mysql` | OK | - |
| `BROADCAST_DRIVER=log` | OK | - |
| `CACHE_DRIVER=file` | OK（生产推荐 redis） | - |
| `QUEUE_CONNECTION=sync` | OK（生产推荐 redis） | - |
| `SESSION_DRIVER=file` | OK（生产推荐 redis/db） | - |
| `SESSION_LIFETIME=120` 分钟 | 较长 | 缩短 |
| `HASH_ROUNDS=10` | OK | - |

### WordPress

| 默认 | 风险 | 修复 |
|---|---|---|
| `wp-admin/` 公开 | 暴力破解 | 限速 + 2FA |
| `wp-login.php` 公开 | 暴力破解 | 改路径 + 限速 |
| `wp-cron.php` 无锁 | 并发重复触发 | 系统 cron |
| `xmlrpc.php` 公开 | 暴力 / DDoS | 关闭 |
| 默认管理员用户名 `admin` | 字典攻击 | 改名 |
| 文件权限 755 / 644 | 可读 | 750 / 640 |

## 4. Node.js / Express

| 默认 | 风险 | 修复 |
|---|---|---|
| 无 helmet | 缺安全头 | `app.use(helmet())` |
| 无 cors | OK | 显式配置 |
| 无 express-rate-limit | DoS / 暴力 | 加 |
| 无 csrf | CSRF | 加 csurf / 手动 token |
| `app.use(express.json({ limit: '100kb' }))` | 默认 100KB（OK） | - |
| 静态 `express.static` 无 index 检查 | 目录列表 | `index: false` |
| `cookie-parser` 无 secret | OK | 仅签名 cookie 需 secret |
| `session-store = MemoryStore` | 内存泄漏 | 用 redis / mongo |
| `process.env.PORT || 3000` | 默认 3000 | OK |
| 信任代理 `trust proxy: false` | OK | 生产按层数设置 |

## 5. Go

| 默认 | 风险 | 修复 |
|---|---|---|
| Gin `gin.Default()` 含 Logger + Recovery | OK | - |
| Gin `gin.SetMode(DebugMode)` (dev) | 详细信息 | ReleaseMode |
| Echo / Fiber 默认无 logger | OK | - |
| `http.Server` 无超时 | Slowloris | `ReadTimeout` / `WriteTimeout` |
| `http.ListenAndServe(":80", nil)` | 监听所有接口 | `:127.0.0.1:80` |
| TLS 配置缺失 | HTTP 明文 | `ListenAndServeTLS` |

## 6. Ruby / Rails

| 默认 | 风险 | 修复 |
|---|---|---|
| `config.force_ssl = false` (dev) | HTTP | true (生产) |
| `config.consider_all_requests_local = true` (dev) | 详细错误 | false (生产) |
| `config.action_controller.allow_forgery_protection = true` | OK | - |
| `config.action_dispatch.show_exceptions = true` (dev) | 详细错误 | false (生产) |
| `config.web_console.whitelisted_ips = ['127.0.0.1', '::1']` | OK (仅本地) | - |
| `config.hosts = []` (Rails 6+) | 任意 host | 显式列表 |
| `config.secret_key_base` 写死 | 密钥泄露 | 环境变量 |
| `Gemfile.lock` 提交 | OK | - |
| `bin/setup` / `bin/deploy` 包含凭据 | 密钥泄露 | 用 secrets manager |

## 7. C# / ASP.NET

| 默认 | 风险 | 修复 |
|---|---|---|
| `<customErrors mode="RemoteOnly"/>` (旧) | 详细错误 | On |
| `<compilation debug="false"/>` (生产) | OK | - |
| `<httpCookies requireSSL="true"/>` (vs) | 嗅探 | true |
| `<httpCookies httpOnlyCookies="true"/>` | XSS | true |
| `<sessionState cookieless="false"/>` | URL session | false |
| `<sessionState cookieSameSite="Lax"/>` (4.7.2+) | CSRF | Strict |
| 视图 `<system.web>` 无 `<machineKey>` | 加密失效 | 显式 |
| WebForms `<pages enableEventValidation="true">` | OK | - |
| MVC 默认开启 AntiForgeryToken | OK | - |
| 默认无 CORS | OK | 显式配置 |
| `services.AddMvc().AddNewtonsoftJson()` 默认 TypeNameHandling=None | OK | - |

## 8. 通用生产清单

| 项 | 修复 |
|---|---|
| `debug` / `DEBUG` / `app.debug` | 关闭 |
| `print stacktrace` | 不暴露给用户 |
| 默认 `admin/admin` 凭据 | 改 + 强制首次登录修改 |
| 测试 / staging 路由 | 关闭 / 限 IP |
| 注释含 `// TODO` / 凭据 | 移除 |
| 提交 `.env` | 加入 `.gitignore` |
| 提交 `application.properties` 含密码 | 移到 secrets manager |
| 注释中含真实 IP | 替换为占位符 |
| 备份 / 旧文件 (`*.bak`, `*.old`, `*.swp`) | 删除 |
| 注释掉的旧代码 | 删除（git log 可查） |
