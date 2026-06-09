# Backend 框架签名

> Agent 在 Phase 1 (Recon) 阶段查阅，用于基于 manifest + 关键文件推断语言与框架。

## 1. 推断流程

```
Step 1: 扫描 manifest
        ├─ pom.xml / build.gradle       → Java
        ├─ requirements.txt / pyproject → Python
        ├─ composer.json                → PHP
        ├─ package.json                 → Node.js / TS
        ├─ go.mod                       → Go
        ├─ Gemfile                      → Ruby
        ├─ *.csproj / *.sln             → C# / .NET
        └─ Cargo.toml                   → Rust

Step 2: 读 manifest 内容匹配具体框架（见下表）
Step 3: 列目录找关键文件（Application.java / app.py / main.go / ...）
Step 4: 输出 framework_profile.json
```

## 2. 框架 → 关键文件 → 入口函数

### Java

| 框架 | manifest 特征 | 关键文件 | 入口函数 |
|---|---|---|---|
| Spring Boot | `spring-boot-starter-*` | `*Application.java` 标 `@SpringBootApplication` | `public static void main` |
| Spring MVC | `spring-webmvc` | `web.xml` + `*-servlet.xml` | `DispatcherServlet` 配置 |
| Spring WebFlux | `spring-webflux` | `*Application.java` | 同 Spring Boot |
| Quarkus | `quarkus-bom` | `*Application.java` | `public static void main` |
| Micronaut | `micronaut-runtime` | `*Application.java` | `public static void main` |
| MyBatis | `mybatis` / `mybatis-plus` | `*Mapper.xml` + `@Mapper` 接口 | XML 内 SQL |
| Hibernate/JPA | `hibernate-core` / `spring-data-jpa` | `*Repository.java` `@Entity` 类 | `JpaRepository` |
| Struts2 | `struts2-core` | `struts.xml` | `<action>` 配置 |
| JFinal | `jfinal` | `*Config.java` | `main(String[] args)` |
| Nutz | `nutz` | `*Module.java` | `@At` 注解 |
| Dubbo | `dubbo` | `dubbo.xml` 或 `@DubboService` | `<dubbo:service>` |
| JSF | `javax.faces` | `faces-config.xml` | `<navigation-rule>` |

### Python

| 框架 | manifest 特征 | 关键文件 | 入口函数 |
|---|---|---|---|
| Django | `Django` | `manage.py` + `settings.py` + `urls.py` | `ROOT_URLCONF.urls` |
| Flask | `Flask` | `app.py` / `wsgi.py` | `app = Flask(__name__)` |
| FastAPI | `fastapi` + `uvicorn` | `main.py` | `app = FastAPI()` |
| Tornado | `tornado` | `app.py` | `Application()` 子类 |
| Sanic | `sanic` | `app.py` | `app = Sanic("...")` |
| aiohttp | `aiohttp` | `app.py` | `web.Application()` |
| Bottle | `bottle` | `app.py` | `Bottle()` |
| Pyramid | `pyramid` | `__init__.py` | `config.include(...)` |
| Falcon | `falcon` | `app.py` | `falcon.App()` |
| Starlette | `starlette` | `app.py` | `Starlette(...)` |
| Celery (worker) | `celery` | `tasks.py` | `@shared_task` |
| Dramatiq | `dramatiq` | `actors.py` | `@dramatiq.actor` |

### PHP

| 框架 | manifest 特征 | 关键文件 | 入口函数 |
|---|---|---|---|
| Laravel | `laravel/framework` | `public/index.php` + `artisan` + `routes/web.php` | `Application::handle` |
| Symfony | `symfony/framework-bundle` | `public/index.php` + `config/routes.yaml` | `Kernel::handle` |
| ThinkPHP | `topthink/framework` | `public/index.php` + `route/route.php` | `App::run` |
| Yii | `yiisoft/yii2` | `web/index.php` + `config/web.php` | `Application::run` |
| CodeIgniter | `codeigniter4/framework` | `public/index.php` | `spark` |
| Slim | `slim/slim` | `public/index.php` | `App::run` |
| Lumen | `laravel/lumen-framework` | `public/index.php` | `Application::run` |
| Phalcon | `phalcon/cphalcon` | `public/index.php` | `Application::handle` |
| Discuz | - | `forum.php` / `home.php` | 自实现路由 |
| WordPress | - | `wp-config.php` + `wp-load.php` | `wp()` |
| Typecho | - | `index.php` + `config.inc.php` | 自实现 |

### Node.js / TypeScript

| 框架 | manifest 特征 | 关键文件 | 入口函数 |
|---|---|---|---|
| Express | `express` | `app.js` / `server.js` / `index.js` | `app.listen()` |
| Koa | `koa` + `@koa/router` | `app.js` | `app.listen()` |
| Fastify | `fastify` | `app.js` | `fastify.listen()` |
| NestJS | `@nestjs/core` + `@nestjs/common` | `main.ts` | `bootstrap()` |
| Hapi | `@hapi/hapi` | `server.js` | `server.start()` |
| Egg | `egg` | `app.js` + `config/config.default.js` | `egg-cluster` |
| Sails | `sails` | `app.js` | `sails.lift()` |
| LoopBack | `@loopback/core` | `src/index.ts` | `RestServer` |
| Restify | `restify` | `server.js` | `server.listen()` |
| Polka | `polka` | `server.js` | `polka()` |
| Next.js | `next` | `pages/*` 或 `app/*` | 文件系统路由 |
| Nuxt | `nuxt` | `pages/*` | 文件系统路由 |
| Remix | `@remix-run/react` | `app/routes/*` | 文件系统路由 |
| Electron | `electron` | `main.js` / `main.ts` | `app.whenReady().then(createWindow)` |

### Go

| 框架 | manifest 特征 | 关键文件 | 入口函数 |
|---|---|---|---|
| Gin | `gin-gonic/gin` | `main.go` | `gin.Default()` + `r.GET/POST` |
| Echo | `labstack/echo` | `main.go` | `echo.New()` |
| Fiber | `gofiber/fiber` | `main.go` | `fiber.New()` |
| Beego | `beego` | `main.go` | `beego.Run()` |
| Iris | `kataras/iris` | `main.go` | `iris.New()` |
| Chi | `go-chi/chi` | `main.go` | `chi.NewRouter()` |
| Revel | `revel/revel` | `app/init.go` | `revel.Run()` |
| Buffalo | `gobuffalo/buffalo` | `actions/app.go` | `App()` |
| Kratos | `kratos` | `cmd/server/main.go` | `kratos.App` |

### Ruby

| 框架 | manifest 特征 | 关键文件 | 入口函数 |
|---|---|---|---|
| Rails | `rails` | `config/application.rb` + `config/routes.rb` | `Application.initialize!` |
| Sinatra | `sinatra` | `app.rb` | `Sinatra::Application` |
| Hanami | `hanami` | `config/app.rb` | `Hanami::App` |
| Grape | `grape` | `app/api.rb` | `class API < Grape::API` |
| Padrino | `padrino` | `config/boot.rb` | `Padrino.application` |
| Cuba | `cuba` | `app.rb` | `Cuba` |

### C# / .NET

| 框架 | manifest 特征 | 关键文件 | 入口函数 |
|---|---|---|---|
| ASP.NET MVC | `Microsoft.AspNet.Mvc` | `Global.asax` + `RouteConfig.cs` | `Application_Start` |
| ASP.NET Core | `Microsoft.AspNetCore.App` | `Program.cs` | `WebApplication.CreateBuilder` |
| ASP.NET Web API | `Microsoft.AspNet.WebApi` | `WebApiConfig.cs` | `Register` |
| NancyFX | `Nancy` | `Bootstrapper.cs` | `NancyModule` |
| ServiceStack | `ServiceStack` | `AppHost.cs` | `AppHost.Configure` |
| Blazor | `Microsoft.AspNetCore.Components` | `Program.cs` | `app.MapBlazorHub` |
| Orleans | `Microsoft.Orleans.Server` | `Program.cs` | `ISiloHost` |
| F# Giraffe | `Giraffe` | `Program.fs` | `WebApplication` |

### Rust

| 框架 | manifest 特征 | 关键文件 | 入口函数 |
|---|---|---|---|
| Actix-web | `actix-web` | `main.rs` | `HttpServer::new(...)` |
| Rocket | `rocket` | `main.rs` | `rocket::build()` |
| Axum | `axum` | `main.rs` | `axum::serve(...)` |
| Warp | `warp` | `main.rs` | `warp::serve(...)` |
| Tide | `tide` | `main.rs` | `tide::new()` |

## 3. 框架特定危险文件

### Java Spring Boot
- `application.yml` / `application.properties` → 密钥、Actuator 配置
- `*.jsp` / `*.html` 模板 → SSTI / XSS
- `*Controller.java` → 路由 + 鉴权
- `*Service.java` → 业务逻辑
- `*Repository.java` / `*Mapper.java` + `*Mapper.xml` → SQL
- `pom.xml` → 危险依赖

### Python Django
- `settings.py` → SECRET_KEY、DEBUG、ALLOWED_HOSTS
- `urls.py` → 路由表
- `views.py` / `models.py` / `forms.py` → 业务 + ORM
- `serializers.py` (DRF) → Mass Assignment
- `permissions.py` (DRF) → 鉴权
- `requirements.txt` → 危险依赖

### Node.js Express
- `app.js` / `server.js` → 中间件链
- `routes/*.js` → 路由
- `controllers/*.js` / `services/*.js` → 业务
- `models/*.js` (Mongoose/Sequelize) → ORM
- `middleware/*.js` → 鉴权 / 校验
- `.env` → 密钥
- `package.json` → 危险依赖

### PHP Laravel
- `routes/web.php` / `routes/api.php` → 路由
- `app/Http/Controllers/*.php` → 控制器
- `app/Models/*.php` → ORM
- `config/*.php` → 配置
- `.env` → 密钥
- `composer.json` → 危险依赖

### Go Gin
- `main.go` → 路由
- `router/*.go` → 路由分组
- `handler/*.go` / `controller/*.go` → 业务
- `service/*.go` → 服务层
- `model/*.go` → 模型
- `go.mod` → 危险依赖

## 4. framework_profile.json 产出样例

```json
{
  "languages": ["java"],
  "primary_language": "java",
  "frameworks": ["spring-boot", "mybatis"],
  "build_tool": "maven",
  "java_version": "17",
  "entry_points": [
    {
      "path": "src/main/java/com/example/Application.java",
      "symbol": "com.example.Application.main",
      "framework": "spring-boot",
      "annotations": ["@SpringBootApplication"]
    }
  ],
  "config_files": [
    "src/main/resources/application.yml"
  ],
  "test_dirs": ["src/test/java"],
  "third_party_deps_count": 42,
  "has_docker": true,
  "has_ci": true,
  "http_listeners": [
    {
      "framework": "spring-boot",
      "default_port": 8080,
      "host": "0.0.0.0",
      "ssl_enabled": false
    }
  ],
  "dangerous_dependencies": [
    {
      "name": "log4j-core",
      "version": "2.13.3",
      "cve": ["CVE-2021-44228"],
      "severity": "Critical"
    }
  ]
}
```
