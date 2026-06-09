# 02 — 框架与入口特征

> 本文档汇总各类语言/框架的"识别指纹"与"入口定位规则"。  
> Agent 在 Phase 1 (Recon) 与 Phase 2 (Entry Discovery) 阶段查阅。

## 2.1 Java / JVM

### 2.1.1 Spring Boot

| 维度 | 特征 |
|---|---|
| Manifest | `pom.xml` 含 `spring-boot-starter-*` / `build.gradle` 含 `org.springframework.boot` |
| 入口 | 类标 `@SpringBootApplication` + `public static void main(String[] args)` |
| 路由 | `@RestController` / `@Controller` + `@RequestMapping` + `@GetMapping`/`@PostMapping`/... |
| 配置 | `application.yml` / `application.properties` / `bootstrap.yml` |
| 启动 | `SpringApplication.run(XxxApplication.class, args)` |
| Actuator | 路径 `/actuator/*` 默认开；2.5 之前无需鉴权 |
| 危险依赖 | `org.apache.logging.log4j:log4j-core` 2.0~2.14.1 (Log4Shell) / `spring-core` < 5.3.18 (Spring4Shell) |

入口扫描正则：
```
@SpringBootApplication
public\s+static\s+void\s+main
```

### 2.1.2 Spring MVC（非 Boot）

| 维度 | 特征 |
|---|---|
| Manifest | `spring-webmvc` 依赖 |
| 入口 | `web.xml` 配 `DispatcherServlet` → `applicationContext.xml` |
| 路由 | `@Controller` + `@RequestMapping(...)` |
| 配置 | `*-servlet.xml` / `@Configuration` 类 |

### 2.1.3 Spring WebFlux

| 维度 | 特征 |
|---|---|
| Manifest | `spring-webflux` |
| 入口 | 同 Spring Boot |
| 路由 | `@RestController` 函数式风格 `RouterFunctions.route(...)` |
| 危险 | Mono/Flux 链中数据竞争 |

### 2.1.4 MyBatis / MyBatis-Plus

| 维度 | 特征 |
|---|---|
| Manifest | `mybatis` / `mybatis-plus` / `mybatis-spring-boot-starter` |
| 路由 | XML mapper (`*Mapper.xml`) + `@Mapper` 接口 |
| 危险 | `${}` 字符串拼接（必须用 `#{}`） |
| 关键 sink | `annotation @Select("...")` / `Provider` 类 SQL 拼接 |

### 2.1.5 Hibernate / JPA

| 维度 | 特征 |
|---|---|
| Manifest | `hibernate-core` / `spring-data-jpa` |
| 入口 | `@Entity` + `@Repository` |
| 危险 | HQL 拼接 / 原生 SQL `createNativeQuery` 拼接 / `EntityManager.createQuery` |
| IDOR | `findById` 未校验 owner |

### 2.1.6 Struts2（历史框架，重点关注）

| 维度 | 特征 |
|---|---|
| Manifest | `struts2-core` |
| 入口 | `struts.xml` `<action>` 配置 |
| 危险 | OGNL 注入（`%{...}` / `${...}`）— S2-045 / S2-048 / S2-057 等漏洞家族 |
| 关键 sink | `<s:property value="...">` / OGNL 表达式执行 |

### 2.1.7 Dubbo

| 维度 | 特征 |
|---|---|
| Manifest | `dubbo` |
| 入口 | `<dubbo:service interface="...">` XML 或 `@DubboService` |
| 危险 | 反序列化（默认 Hessian2） + 默认无鉴权 + 默认开 20880 端口 |

### 2.1.8 危险依赖清单

| 组件 | 版本范围 | CVE |
|---|---|---|
| log4j-core | 2.0~2.14.1 | CVE-2021-44228 (Log4Shell) |
| log4j-core | 2.0~2.15.0 | CVE-2021-45046 |
| spring-core | < 5.3.18 | CVE-2022-22965 (Spring4Shell) |
| spring-cloud | < 2021.0.1 | CVE-2022-22963 (SpEL RCE) |
| fastjson | < 1.2.83 | 反序列化 RCE |
| jackson-databind | < 2.9.10.7 | 反序列化 RCE |
| snakeyaml | < 2.0 | 反序列化 RCE（`Yaml.load`） |
| xstream | < 1.4.18 | 反序列化 RCE |
| commons-collections | < 3.2.2 / 4-4.1 | 反序列化 gadget |
| shiro | < 1.7.1 | CVE-2020-17510 / 17523 |

## 2.2 Python

### 2.2.1 Django

| 维度 | 特征 |
|---|---|
| Manifest | `Django>=` in requirements / `django` in pyproject |
| 入口 | `manage.py` + `settings.py` 中 `ROOT_URLCONF` |
| 路由 | `urls.py` 含 `path(...)` / `re_path(...)` / `include(...)` |
| 控制器 | `views.py` 函数式或 `View` 类 |
| ORM | `models.py` `Model.objects.filter(...)` |
| 模板 | `templates/*.html` `{{ var }}` |
| 配置 | `settings.py` 中 `DEBUG`、`ALLOWED_HOSTS`、`SECRET_KEY` |
| 危险 | `DEBUG=True` 暴露堆栈 / `SECRET_KEY` 提交仓库 / `render(request, ...)` 受控但 `mark_safe` 可绕过 |

### 2.2.2 Flask

| 维度 | 特征 |
|---|---|
| Manifest | `Flask>=` in requirements |
| 入口 | `app = Flask(__name__)` + `app.run()` 或 `flask run` |
| 路由 | `@app.route("/path", methods=[...])` |
| 配置 | `app.config[...]` / 配置文件 |
| 危险 | `render_template_string(f"...{user_input}...")` SSTI / `app.run(debug=True)` / `SECRET_KEY` 写死 / `session` 客户端可解码 |

### 2.2.3 FastAPI

| 维度 | 特征 |
|---|---|
| Manifest | `fastapi>=` |
| 入口 | `app = FastAPI()` + `uvicorn app:app` |
| 路由 | `@app.get("/path")` / `@app.post(...)` |
| 危险 | 路径参数未校验（`path: str` 而非 `path: int`）/ `eval` 配置文件 / OAuth2 scope 未强制 |

### 2.2.4 危险依赖

| 组件 | 危险 |
|---|---|
| `pyyaml<5.1` | `yaml.load()` 反序列化 |
| `pillow<8.3.2` | 图像处理 RCE |
| `paramiko<2.7.2` | SSH 私钥校验 |
| `cryptography<3.3.2` | OpenSSL 漏洞 |
| `jinja2` | 模板不当使用导致 SSTI |
| `pymongo<3.11` | `$where` 注入 |
| `requests` | 跟随重定向 → SSRF |
| `tornado` | 模板注入 |
| `aiohttp` | 路径遍历（CVE-2024-23334） |

## 2.3 PHP

### 2.3.1 Laravel

| 维度 | 特征 |
|---|---|
| Manifest | `laravel/framework` |
| 入口 | `public/index.php` + `bootstrap/app.php` + `artisan` |
| 路由 | `routes/web.php` / `routes/api.php` 中 `Route::get(...)` |
| 控制器 | `app/Http/Controllers/*.php` |
| ORM | Eloquent `Model::where(...)` (默认参数化) / `whereRaw(...)` 危险 |
| 模板 | Blade `*.blade.php` `{{ }}` 默认转义，`{!! !!}` 不转义 |
| 配置 | `.env` + `config/*.php` |
| 危险 | `APP_DEBUG=true` / `APP_KEY` 提交 / `unserialize` / 动态 include |

### 2.3.2 ThinkPHP

| 维度 | 特征 |
|---|---|
| Manifest | `thinkphp` / `topthink/framework` |
| 入口 | `public/index.php` + `think` 启动 |
| 路由 | `route/route.php` + 注解路由 |
| 危险 | 历史多次 RCE：CVE-2018-20062 / CVE-2019-9082 / CVE-2022-47945（多语言 RCE） |
| 关键 sink | `think\Container::get` / `Route::get` 参数未过滤 / 模板 `think\Template` |

### 2.3.3 WordPress

| 维度 | 特征 |
|---|---|
| Manifest | `wp-config.php` + `wp-content/` |
| 入口 | `wp-admin/` + `wp-login.php` |
| 危险 | 插件漏洞（千万级 CVE 库）/ `wp-config.php` 数据库密码 / `wp-cron.php` |

### 2.3.4 通用 PHP 危险

| 函数 | 类别 |
|---|---|
| `eval` / `assert` / `create_function` / `preg_replace /e` | 代码执行 |
| `system` / `exec` / `passthru` / `popen` / `proc_open` / 反引号 `` `cmd` `` | 命令执行 |
| `unserialize` / `phar` | 反序列化 |
| `include` / `require` / `include_once` / `require_once` 动态参数 | LFI/RFI |
| `file_get_contents` / `fopen` / `readfile` 用户输入 | 文件读取 |
| `mysql_query` / `mysqli_query` 拼接 | SQLi |
| `echo $_GET[...]` / `print` 未转义 | XSS |
| `header("Location: $url")` 用户输入 | Open Redirect |
| `curl_setopt($ch, CURLOPT_URL, $_GET[...])` | SSRF |
| `extract($_GET)` / `parse_str` / `import_request_variables` | 变量覆盖 |

## 2.4 Node.js / TypeScript

### 2.4.1 Express

| 维度 | 特征 |
|---|---|
| Manifest | `express` in package.json |
| 入口 | `app = express()` + `app.listen(port)` |
| 路由 | `app.get(path, handler)` / `app.post(...)` / `app.use(...)` |
| 中间件 | `app.use((req, res, next) => {...})` |
| 模板 | `res.render(view, data)` / Pug / EJS |
| 危险 | `res.send(user_input)` 无转义 / `eval` / `child_process.exec` 拼接 / `Object.assign` 原型链污染 / `req.query` 透传 DB |

### 2.4.2 NestJS

| 维度 | 特征 |
|---|---|
| Manifest | `@nestjs/core` + `@nestjs/common` |
| 入口 | `main.ts` `NestFactory.create(AppModule)` |
| 路由 | `@Controller('path')` + `@Get()` / `@Post()` / `@Body()` / `@Param()` |
| 危险 | 装饰器 `Body()` 不带 `class-validator` / 全局 `ValidationPipe` 缺失 |

### 2.4.3 Koa / Fastify / Egg

入口大同小异：`new Koa()` / `fastify()` / `egg.App`。

### 2.4.4 危险依赖

| 组件 | 危险 |
|---|---|
| `lodash<4.17.21` | 原型链污染 (`_.merge`) |
| `minimist<1.2.6` | 原型链污染 |
| `node-serialize` | 反序列化 RCE |
| `js-yaml<4.1.0` | 反序列化 (`yaml.load` 无 schema) |
| `axios<1.6.0` | SSRF (跟随重定向) |
| `jsonwebtoken<9.0.0` | alg=none 攻击 |
| `ejs` | 模板注入 |
| `pug` | 模板注入 |

### 2.4.5 原型链污染 sink

```js
// 关键模式
_.merge(target, source)        // lodash
_.set(object, path, value)     // lodash
Object.assign(target, source)  // 原生
$.extend(true, target, source) // jQuery
deepMerge(target, source)      // 自写
```

触发条件：path 含 `__proto__` / `constructor.prototype`。

## 2.5 Go

### 2.5.1 Gin

| 维度 | 特征 |
|---|---|
| Manifest | `gin-gonic/gin` |
| 入口 | `func main()` + `gin.Default()` |
| 路由 | `r := gin.Default()` + `r.GET("/path", handler)` |
| 参数 | `c.Param("id")` / `c.Query("name")` / `c.PostForm(...)` / `c.ShouldBindJSON(&obj)` |
| 危险 | 命令拼接 `exec.Command("sh", "-c", "..."+userInput)` / SQL 拼接 / SSRF（`http.Get(userInput)`） |

### 2.5.2 Echo / Fiber / Beego

| 维度 | 特征 |
|---|---|
| Echo | `e := echo.New()` + `e.GET("/path", h)` |
| Fiber | `app := fiber.New()` + `app.Get("/path", h)` |
| Beego | `beego.Run()` + `beego.Router(...)` |

### 2.5.3 通用 Go 危险

```go
os.Exec(userInput)              // 命令执行
exec.Command("sh", "-c", user)  // 拼接
fmt.Sprintf("SELECT * FROM x WHERE id = %s", id)  // SQLi
http.Get(userInput)             // SSRF
os.Open(userInput)              // 路径遍历
template.HTML(userInput)        // XSS (html/template)
io.ReadAll(http.GetBody(...))   // 资源耗尽
```

## 2.6 Ruby

### 2.6.1 Rails

| 维度 | 特征 |
|---|---|
| Manifest | `rails` in Gemfile |
| 入口 | `config/application.rb` + `bin/rails` |
| 路由 | `config/routes.rb` 中 `resources :users` / `get 'path', to: ...` |
| 控制器 | `app/controllers/*.rb` |
| ORM | ActiveRecord `Model.where("name = '#{params[:name]}'")` (危险) / `where(name: params[:name])` (安全) |
| 模板 | `.erb` / `.haml` / `.slim` |
| 危险 | `render inline: "..."` / strong params 缺失 / 开放重定向 / SQL 字符串插值 |

### 2.6.2 Sinatra / Hanami / Grape

入口不同，模式类似。

### 2.6.3 通用 Ruby 危险

```ruby
eval(user_input)              # RCE
system(user_input)            # 命令
`#{user_input}`               # 反引号命令
open("| #{user_input}")       # 管道
YAML.load(user_input)         # 反序列化
Marshal.load(user_input)      # 反序列化
ERB.new(user_input).result    # SSTI
send(user_method, *args)      # 动态调用
```

## 2.7 C# / .NET

### 2.7.1 ASP.NET MVC

| 维度 | 特征 |
|---|---|
| Manifest | `*.csproj` 含 `<PackageReference Include="Microsoft.AspNet.Mvc"/>` |
| 入口 | `Global.asax` / `Startup.cs` (`ASP.NET Core`) |
| 路由 | `RouteConfig.cs` + `[Route]` 特性 |
| 控制器 | `*Controller.cs` |
| 视图 | `*.cshtml` Razor 引擎 |
| 危险 | `@Html.Raw(model.UserInput)` XSS / `ConfigurationManager.AppSettings` 读密码 / 关闭 AntiForgeryToken |

### 2.7.2 ASP.NET Core

| 维度 | 特征 |
|---|---|
| Manifest | `Microsoft.AspNetCore.App` |
| 入口 | `Program.cs` `WebApplication.CreateBuilder(args)` |
| 路由 | `[ApiController]` + `[Route("api/[controller]")]` + `[HttpGet]` |
| 危险 | `services.AddCors(...)` 全开 / `app.UseAuthentication` 缺失 / `AllowAnonymous` 滥用 |

### 2.7.3 通用 .NET 危险

```csharp
Process.Start("cmd.exe", "/c " + userInput)  // 命令
new SqlCommand("SELECT ... " + userInput)     // SQLi
XmlDocument.Load(userInput)                  // XXE
new JavaScriptSerializer().Deserialize(userInput)  // 反序列化
BinaryFormatter.Deserialize(stream)          // 反序列化
HttpContext.Current.Request["..."]           // XSS 直接输出
Path.Combine(allowPath, userInput)           // 路径遍历（需额外校验）
```

## 2.8 前端框架

### 2.8.1 Vue 2 / Vue 3

| 维度 | 特征 |
|---|---|
| 入口 | `new Vue({...})` (Vue 2) / `createApp(...).mount('#app')` (Vue 3) |
| 模板 | `*.vue` 单文件组件 `<template>` `<script>` `<style>` |
| 路由 | `vue-router` 配置 `routes: [{ path, component }]` |
| 状态 | `vuex` / `pinia` |
| 危险 sink | `v-html="userInput"` / `{{ }}` (Vue 2 无 v-html 也可注入，但默认转义) / `{{ }}` (Vue 3 默认转义) / 模板 `{{ }}` 拼接表达式 |
| 存储 | `localStorage` / `sessionStorage` 存 token / cookie |
| 路由守卫 | `router.beforeEach` 鉴权逻辑漏洞 |

### 2.8.2 React

| 维度 | 特征 |
|---|---|
| 入口 | `ReactDOM.createRoot(...).render(<App/>)` / `ReactDOM.render(...)` (legacy) |
| 组件 | `*.jsx` / `*.tsx` |
| 路由 | `react-router-dom` `createBrowserRouter` / `<BrowserRouter>` |
| 状态 | `redux` / `mobx` / `zustand` / `recoil` |
| 危险 sink | `dangerouslySetInnerHTML={{__html: userInput}}` / `href={userInput}` (javascript:) / `eval` / `setTimeout(string, ...)` |
| 状态 | store 中存敏感数据（应只在内存） |
| API | `axios` / `fetch` 缺 CSRF / 鉴权头 |

### 2.8.3 Angular

| 维度 | 特征 |
|---|---|
| 入口 | `bootstrapModule(AppModule)` |
| 路由 | `RouterModule.forRoot(routes)` |
| 危险 sink | `[innerHTML]="userInput"` (需 bypassDomSanitizer) / `bypassSecurityTrustHtml` / `bypassSecurityTrustScript` / `bypassSecurityTrustUrl` / `bypassSecurityTrustResourceUrl` |
| 模板 | Angular 模板默认转义，但 `innerHTML` 配合 bypass 即危险 |

### 2.8.4 Svelte

| 维度 | 特征 |
|---|---|
| 入口 | `new App({target: ...})` |
| 危险 | `{@html userInput}` (Svelte 等价 v-html) |

### 2.8.5 jQuery / Vanilla

| 维度 | 特征 |
|---|---|
| 危险 | `.html(userInput)` / `.append(userInput)` / `$()` / `$.parseHTML` / `eval` / `setTimeout(string, ...)` / `document.write` / `location.hash` + `eval` |
| DOM-XSS | `URL` 参数 → `eval` / `setAttribute` / `setInterval` |

## 2.9 通用配置文件

### 2.9.1 高危默认配置

| 配置 | 风险 |
|---|---|
| `DEBUG = True` (Django) / `debug: true` (Spring) / `FLASK_DEBUG=1` | 暴露堆栈/控制台 |
| `ALLOWED_HOSTS = ['*']` (Django) | Host header injection |
| `SECRET_KEY = 'xxx'` 写死 | Session 可伪造 |
| `app.run(debug=True)` | 远程代码执行 (Werkzeug PIN) |
| `spring.main.banner-mode = off` 无关，但 `spring.devtools.restart.enabled = true` 生产开启 | 远程重启 |
| `management.endpoints.web.exposure.include = '*'` (Actuator) | 信息泄露 |
| `server.error.include-stacktrace = always` | 堆栈泄露 |
| `mybatis.configuration.map-underscore-to-camel-case = true` 不影响安全 | - |
| `CORS_ALLOW_ALL_ORIGINS = True` (Django) / `app.use(cors())` 无配置 | CSRF 失效 |
| `JWT_SECRET = 'changeit'` / 短 | 签名可爆破 |
| `session.cookie.secure = False` | 嗅探 |
| 注释中的真实凭据 / 内部 URL | 信息泄露 |

### 2.9.2 危险 .env / .properties 字段

```
DATABASE_URL=
REDIS_URL=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
SENDGRID_API_KEY=
GITHUB_TOKEN=
JWT_SECRET=
SESSION_SECRET=
SMTP_PASSWORD=
```

凡是仓库内 .env / .properties / config.yaml 出现这些字段，**警告但不立即升级为 finding**（可能在 .gitignore 内 → 需 LLM 判断）。

## 2.10 路由表抽取规则（跨语言）

| 框架 | 抽取方式 |
|---|---|
| Spring | 扫描 `@RequestMapping` / `@GetMapping` / `@PostMapping` / `@PutMapping` / `@DeleteMapping` / `@PatchMapping` 上的 path + method |
| Django | 解析 `urls.py` 中 `path(...)` / `re_path(...)` / `include(...)` |
| Flask | 扫描 `@app.route` / `@blueprint.route` / `@api.route` 上的 path + methods |
| FastAPI | 扫描 `@app.get` / `@app.post` / ... 装饰器 |
| Express | 扫描 `app.get/post/put/delete/patch` / `router.get/post/...` 调用 |
| Koa | 扫描 `router.get/post/...` |
| NestJS | 扫描 `@Controller('path')` + 方法上的 `@Get` / `@Post` |
| Laravel | 解析 `routes/web.php` / `routes/api.php` 中 `Route::xxx(...)` |
| Symfony | 解析 `routes.yaml` / `*.yaml` |
| Gin | 扫描 `r.GET/POST/PUT/DELETE/PATCH/OPTIONS/HEAD(...)` |
| Echo | 扫描 `e.GET/POST/...` |
| Rails | 解析 `config/routes.rb` |
| ASP.NET MVC | 扫描 `[Route]` / `[HttpGet]` / `[HttpPost]` 特性 |
| ASP.NET Core | 同上 |

输出统一为：
```json
{
  "method": "GET",
  "path": "/api/user/{id}",
  "file": "UserController.java",
  "line": 42,
  "class_or_route": "UserController#getUser",
  "auth_annotation": "@PreAuthorize",
  "params": [{"name": "id", "location": "path", "type": "int"}]
}
```
