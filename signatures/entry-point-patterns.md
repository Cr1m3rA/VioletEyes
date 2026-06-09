# 入口点模式 (Entry Point Patterns)

> Agent 在 Phase 2 (Entry Discovery) 阶段查阅，用于在仓库内自动定位所有 HTTP 入口（路由）。

## 1. 入口点分类

| 类别 | 说明 | 风险 |
|---|---|---|
| HTTP API 入口 | Controller / Router / Handler | 主要审计目标 |
| GraphQL 入口 | `app.use('/graphql', expressGraphQL(...))` | API Top 10 |
| WebSocket 入口 | `WebSocketRoute` / `socket.io` | 鉴权 / 注入 |
| gRPC 入口 | `ServerServiceDefinition` | 一般不审 |
| CLI 入口 | `argparse` / `click` / `yargs` | 内部为主 |
| 定时任务 | `cron` / `celery beat` / `@Scheduled` | 参数污染 |
| 消息队列消费者 | `kafka consumer` / `rabbit consumer` | 消息体注入 |
| Admin 后台 | `/admin` / `wp-admin` / Django admin | 高价值目标 |

## 2. 入口点定位算法

```
Step 1: 找框架主入口
        - 见 backend-frameworks.md 关键文件
Step 2: 读入口文件，提取路由注册
Step 3: 对每个路由，定位 handler 函数
Step 4: 输出 routes.json
```

## 3. 跨语言路由模式

### 3.1 Java Spring

```java
// 注解风格（Spring 4+）
@RestController
@RequestMapping("/api/users")
public class UserController {
    @GetMapping("/{id}")        // GET /api/users/{id}
    @PostMapping               // POST /api/users
    @PutMapping("/{id}")       // PUT /api/users/{id}
    @DeleteMapping("/{id}")    // DELETE /api/users/{id}
    @PatchMapping("/{id}")     // PATCH /api/users/{id}
    
    @GetMapping(path = "/{id}", headers = "X-API-Version=1")
    public User getUser(@PathVariable Long id) { ... }
    
    // 鉴权注解（重要！）
    @PreAuthorize("hasAuthority('USER')")
    @Secured("ROLE_USER")
    @RolesAllowed("USER")
    @PostAuthorize("returnObject.owner == authentication.name")
}

// 函数式风格（Spring 5+ WebFlux）
@Bean
public RouterFunction<ServerResponse> routes(UserHandler h) {
    return route(GET("/users/{id}"), h::get)
           .andRoute(POST("/users"), h::create);
}
```

Agent 提取：注解 + 路径前缀 + 类 + 方法 + 鉴权注解

### 3.2 Java JFinal / Nutz / Dubbo

```java
// JFinal
public class UserController extends Controller {
    public void index() { render("user.html"); }   // 默认路径 /user
    @ActionKey("/login")                          // 显式路径
    public void login() { ... }
}

// Nutz
@At("/user")
public class UserModule {
    @At("/get")
    @Ok("json")
    public User get(@Param("id") long id) { ... }
}

// Dubbo
<dubbo:service interface="com.x.UserService" ref="userService"/>
// @DubboService
```

### 3.3 Python Django

```python
# urls.py
from django.urls import path, re_path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/<int:id>/', views.get_user, name='user-detail'),
    re_path(r'^users/(?P<id>\d+)/$', views.get_user),
    path('api/v1/', include('api.urls')),
]

# views.py
def get_user(request, id):
    return JsonResponse(...)

# ViewSet (DRF)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # 自动生成 list/retrieve/create/update/destroy
```

Agent 提取：path 参数 → regex 解析 → views 函数 / 类

### 3.4 Python Flask

```python
from flask import Flask, Blueprint
app = Flask(__name__)
api = Blueprint('api', __name__, url_prefix='/api')

@app.route('/users/<int:id>', methods=['GET'])
def get_user(id):
    return ...

@app.route('/login', methods=['POST'])
def login():
    return ...

@api.route('/items', methods=['GET'])
def list_items():
    return ...
```

Agent 提取：所有 `@app.route` / `@blueprint.route` / `@api.route` 装饰器

### 3.5 Python FastAPI

```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return ...

@app.post("/users")
async def create_user(user: UserCreate):
    return ...

@app.put("/users/{user_id}")
async def update_user(user_id: int, user: UserUpdate):
    return ...

# APIRouter
router = APIRouter(prefix="/v1")
@router.get("/items/{item_id}")
async def get_item(item_id: int):
    return ...
```

Agent 提取：所有 `@app.<method>` / `@router.<method>` 装饰器

### 3.6 Node.js Express

```js
const express = require('express');
const router = express.Router();
const app = express();

// App-level
app.get('/users/:id', handler);
app.post('/users', handler);
app.put('/users/:id', handler);
app.delete('/users/:id', handler);
app.patch('/users/:id', handler);
app.all('/users', handler);
app.use('/api', subRouter);
app.use(authMiddleware);
app.use('/static', express.static('public'));

// Router
router.get('/items/:id', handler);
router.post('/items', handler);
```

Agent 提取：所有 `app.<method>` / `router.<method>` / `app.use` 调用

### 3.7 Node.js NestJS

```typescript
@Controller('users')
export class UserController {
    @Get(':id')          // GET /users/:id
    @Post()              // POST /users
    @Put(':id')          // PUT /users/:id
    @Delete(':id')       // DELETE /users/:id
    @Patch(':id')        // PATCH /users/:id
    
    @Get(':id')
    @UseGuards(JwtAuthGuard)
    @Roles('admin')
    async getUser(@Param('id') id: string) { ... }
}
```

Agent 提取：类 + `@Controller(prefix)` + 方法 + 方法级 `@<Http>()` + `@UseGuards` + `@Roles`

### 3.8 Node.js Koa / Fastify

```js
// Koa
const router = new Router();
router.get('/users/:id', handler);
router.post('/users', handler);

// Fastify
fastify.get('/users/:id', handler);
fastify.post('/users', handler);
fastify.route({
    method: 'GET',
    url: '/users/:id',
    handler
});
```

### 3.9 PHP Laravel

```php
// routes/web.php / routes/api.php
use App\Http\Controllers\UserController;

Route::get('/users/{id}', [UserController::class, 'show']);
Route::post('/users', [UserController::class, 'store']);
Route::put('/users/{id}', [UserController::class, 'update']);
Route::patch('/users/{id}', [UserController::class, 'update']);
Route::delete('/users/{id}', [UserController::class, 'destroy']);

Route::resource('users', UserController::class);  // RESTful
Route::apiResource('users', UserController::class);  // RESTful no create/edit

// Middleware
Route::middleware('auth:sanctum')->group(function () {
    Route::get('/profile', ...);
});

// Group
Route::prefix('admin')->middleware('auth')->group(function () {
    Route::get('/dashboard', ...);
});
```

Agent 提取：所有 `Route::<method>(...)` + `Route::resource` + `Route::apiResource` + `Route::group` + 中间件

### 3.10 PHP Symfony

```yaml
# config/routes.yaml
users_list:
    path: /users
    methods: [GET]
    controller: App\Controller\UserController::list

users_show:
    path: /users/{id}
    methods: [GET]
    controller: App\Controller\UserController::show
```

```php
// Annotation (Symfony 5-)
use Symfony\Component\Routing\Annotation\Route;

class UserController {
    /**
     * @Route("/users/{id}", methods={"GET"})
     */
    public function show(int $id) { ... }
}
```

### 3.11 PHP ThinkPHP

```php
// route/route.php
use think\facade\Route;

Route::get('users/:id', 'UserController/read');
Route::post('users', 'UserController/create');

// 注解路由 (ThinkPHP 6)
#[Route('GET', 'users/:id')]
public function read($id) { ... }
```

### 3.12 Go Gin

```go
r := gin.Default()

r.GET("/users/:id", getUser)
r.POST("/users", createUser)
r.PUT("/users/:id", updateUser)
r.DELETE("/users/:id", deleteUser)
r.PATCH("/users/:id", patchUser)

// Group
v1 := r.Group("/api/v1")
{
    v1.GET("/users/:id", getUser)
    v1.POST("/users", createUser)
}

// Middleware
r.GET("/admin", authMiddleware(), adminHandler)
```

Agent 提取：所有 `r.<METHOD>(path, ...handlers)` + Group 路径前缀

### 3.13 Go Echo / Fiber

```go
// Echo
e := echo.New()
e.GET("/users/:id", getUser)
e.POST("/users", createUser)
g := e.Group("/api/v1")
g.GET("/users/:id", getUser)

// Fiber
app := fiber.New()
app.Get("/users/:id", getUser)
app.Post("/users", createUser)
app.Use("/api", apiGroup)
```

### 3.14 Ruby Rails

```ruby
# config/routes.rb
Rails.application.routes.draw do
    resources :users  # 自动生成 7 个 RESTful 路由
    
    get 'profile', to: 'users#profile'
    post 'login', to: 'sessions#create'
    
    namespace :admin do
        resources :users  # /admin/users
    end
    
    scope path: '/api', module: 'api' do
        resources :users  # /api/users
    end
end
```

Agent 提取：`resources` / `get/post/put/delete/patch` + 命名空间

### 3.15 C# / .NET

```csharp
// ASP.NET Core
[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase {
    [HttpGet("{id}")]        // GET api/users/{id}
    [HttpPost]                // POST api/users
    [HttpPut("{id}")]         // PUT api/users/{id}
    [HttpDelete("{id}")]      // DELETE api/users/{id}
    [HttpPatch("{id}")]       // PATCH api/users/{id}
    
    [HttpGet("{id}")]
    [Authorize(Roles = "Admin")]
    public IActionResult GetUser(int id) { ... }
    
    [HttpGet]
    [AllowAnonymous]
    public IActionResult List() { ... }
}

// Minimal API (.NET 6+)
app.MapGet("/users/{id}", (int id) => { ... });
app.MapPost("/users", (User u) => { ... });
```

Agent 提取：类 + `[Route]` + 方法 + `[Http<Method>]` + `[Authorize]` / `[AllowAnonymous]`

## 4. 路径参数识别

| 框架 | 路径参数语法 | 类型注解 |
|---|---|---|
| Spring | `{id}` | `@PathVariable Long id` |
| Django | `<int:id>` / `<str:name>` | 函数参数 |
| Flask | `<int:id>` / `<string:name>` | 函数参数 |
| FastAPI | `{user_id}` | `user_id: int` |
| Express | `:id` | `req.params.id` |
| Koa | `:id` | `ctx.params.id` |
| NestJS | `:id` | `@Param('id')` |
| Laravel | `{id}` | 函数参数 |
| Symfony | `{id}` | 函数参数 |
| Gin | `:id` | `c.Param("id")` |
| Echo | `:id` | `c.Param("id")` |
| Fiber | `:id` | `c.Params("id")` |
| Rails | `:id` | `params[:id]` |
| ASP.NET | `{id}` | 函数参数 |

## 5. 鉴权注解 / 中间件识别

| 框架 | 鉴权标记 | 含义 |
|---|---|---|
| Spring | `@PreAuthorize` / `@Secured` / `@RolesAllowed` | 前置鉴权 |
| Spring | `@PostAuthorize` | 后置鉴权 |
| Spring Security | `SecurityFilterChain` 配置 | 全局 |
| Express | `app.use(authMiddleware)` / `passport.authenticate` | 中间件 |
| NestJS | `@UseGuards(AuthGuard)` | 守卫 |
| NestJS | `@Roles('admin')` + `RolesGuard` | 角色 |
| Laravel | `->middleware('auth:sanctum')` | 路由组 |
| Laravel | `Gate::define` / `Policy` | 策略 |
| Django | `@login_required` / `LoginRequiredMixin` | 视图装饰器 |
| Django | `IsAuthenticated` (DRF) | 权限类 |
| Flask | `@login_required` / `@requires_auth` | 装饰器 |
| Gin | `r.Use(authMiddleware)` / `authMiddleware()` 内联 | 中间件 |
| Rails | `before_action :authenticate` | 控制器过滤器 |
| Rails | `pundit` / `cancancan` | 策略 |
| ASP.NET | `[Authorize]` / `[Authorize(Roles="admin")]` | 特性 |
| ASP.NET | `app.UseAuthentication()` | 中间件 |

**IDOR 推断规则**：
- 路由未标任何鉴权 → 默认 IDOR 风险（除非全局 middleware 启用）
- 路由仅标 `@PreAuthorize("isAuthenticated()")` → 仍可能有 IDOR（仅认证未鉴权）
- 路由标 `@PreAuthorize("hasAuthority('USER')")` 且 handler 内手动校验 owner → 安全
- 路由标鉴权但 handler 内无 owner 校验 → 仍可能有 IDOR（横向越权）

## 6. GraphQL 入口

```js
// Apollo Server
const server = new ApolloServer({
    typeDefs,
    resolvers,
    // 注意：禁用 introspection 在生产
    introspection: process.env.NODE_ENV !== 'production',
});
```

```python
# Graphene
class Query(ObjectType):
    user = Field(UserType, id=Int(required=True))
    def resolve_user(self, info, id):
        return User.objects.get(id=id)
```

```php
# Laravel GraphQL
type Query {
    user(id: ID!): User @guard
}
```

Agent 抽取：所有 `@Query` / `@Mutation` / `Field` 装饰的 resolver

## 7. WebSocket 入口

```js
// Express + ws / Socket.IO
io.on('connection', (socket) => {
    socket.on('chat', (msg) => { ... });     // 消息处理器
});

// NestJS
@WebSocketGateway()
export class ChatGateway {
    @SubscribeMessage('message')
    handleMessage(@MessageBody() data: any) { ... }
}
```

```python
# FastAPI
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        ...
```

```go
// Gorilla
hub := newHub()
http.HandleFunc("/ws", func(w, r) {
    conn, _ := upgrader.Upgrade(w, r, nil)
    // ...
})
```

## 8. CLI 入口（次要）

```python
# Click
@click.command()
@click.option('--name')
def main(name):
    print(f"Hello {name}")
```

```js
// Commander
program
    .command('exec <cmd>')
    .action((cmd) => exec(cmd));
```

CLI 入口风险：参数直接传给 shell / eval / 拼接 SQL（典型 sysadmin 工具漏洞）

## 9. 入口点产出物

```json
[
  {
    "id": "AST-0001",
    "type": "http_api",
    "language": "java",
    "framework": "spring-boot",
    "file_path": "src/main/java/com/x/UserController.java",
    "file_line": 42,
    "class_or_route": "UserController#getUser",
    "method": "GET",
    "url_or_path": "/api/users/{id}",
    "path_params": [{"name": "id", "type": "long", "annotation": "@PathVariable"}],
    "query_params": [],
    "body_params": [],
    "auth_required": true,
    "auth_mechanism": "@PreAuthorize(\"hasAuthority('USER')\")",
    "auth_granularity": "authenticated_only",  // authenticated | role-based | owner-checked
    "tags": ["user-data", "pii"]
  }
]
```
