# Workflow: Frontend Audit（前端专项审计）

> 聚焦 Vue / React / Angular / Svelte / jQuery 等前端代码，审计 XSS、客户端存储、路由守卫、原型链污染等。

## 触发条件

- `mode=frontend-focused`
- 适合 SPA / 前后端分离项目
- 也适合微前端 / monorepo 中的 frontend 目录

## 步骤

### Step 1: 入口定位

```bash
# 找前端入口
ls src/main.* src/App.* src/index.* 2>/dev/null
cat package.json | grep -E '"(vue|react|@angular/core|svelte|next|nuxt|electron)"'
```

确定框架后，按 `signatures/frontend-frameworks.md` 抽取：
- 路由表（vue-router / react-router / Angular Router）
- 全局状态（Vuex / Pinia / Redux / MobX / Zustand）
- HTTP 客户端（axios / fetch 封装）

### Step 2: 危险 sink 扫描

```bash
# 扫描 XSS sink
grep -rn "v-html=" src/                 # Vue
grep -rn "dangerouslySetInnerHTML" src/  # React
grep -rn "bypassSecurityTrust" src/      # Angular
grep -rn "{@html" src/                  # Svelte
grep -rn "\.html(" src/                 # jQuery
grep -rn "innerHTML\s*=" src/            # Vanilla

# 扫描 eval / new Function
grep -rnE "\beval\s*\(" src/
grep -rnE "new\s+Function\s*\(" src/
grep -rnE "setTimeout\s*\(\s*['\"]" src/
grep -rnE "setInterval\s*\(\s*['\"]" src/
```

### Step 3: 客户端存储审计

```bash
grep -rnE "localStorage\.(setItem|getItem)" src/
grep -rnE "sessionStorage\.(setItem|getItem)" src/
grep -rnE "document\.cookie" src/
```

判定：
- 是否有 token / PII 存入 localStorage？→ 警告
- cookie 是否无 httpOnly / secure / sameSite？→ 警告

### Step 4: 路由守卫审计

```js
// 找到 router 配置
const routes = ...

// 审查每个路由的 meta.requiresAuth
// 审查 beforeEach / onBeforeRouteEnter
// 审查 <ProtectedRoute> 组件
```

判定：
- 关键路由无守卫？→ 警告
- 守卫仅前端校验（无后端鉴权）？→ 警告（前端绕过）
- 守卫逻辑有缺陷（如 `if (localStorage.getItem('token'))`）？→ 警告

### Step 5: 第三方依赖

读 `package.json` 检查：
- `dompurify` / `marked` / `jquery` 版本
- 是否使用 `lodash` 的 `_.merge`（原型链污染）
- 是否使用 `axios < 1.6.0`（CSRF token 泄露）
- 是否使用 `serialize-javascript` / `node-serialize`（反序列化）

### Step 6: 报告

```
报告标题: code-audit-report.html (frontend-focused)
封面:
  - 模式: frontend-focused
  - 框架: Vue 3
  - 路由数: 24
  - 状态管理: Pinia
  - 重点审计: XSS / 客户端存储 / 路由守卫
banner: "🎨 Frontend-focused audit — XSS / 客户端存储 / 路由守卫"
```

## 输出

- `frontend-assets.json` — 组件 / 路由
- `findings.json` — 漏洞
- `code-audit-report.html` — 报告

## 不适用：第三方依赖 CVE 扫描（V1.2）

前端专项默认由 `full-audit` 阶段覆盖依赖扫描。`Step 5: 第三方依赖` 仅做版本号提示性检查；如需深度联网匹配，请单独运行 `cve_lookup.py`。
