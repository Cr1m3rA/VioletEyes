# Example: Vue 3 + React 审计

> 演示对前端项目（Vue 3 / React）的 XSS / 客户端存储 / 路由守卫审计。

## 1. Vue 3 项目结构

```
vue3-admin/
├── package.json
├── vite.config.ts
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/
│   │   └── index.ts
│   ├── views/
│   │   ├── Dashboard.vue
│   │   ├── UserProfile.vue
│   │   └── admin/
│   │       └── AdminPanel.vue
│   ├── components/
│   │   └── RichText.vue
│   ├── stores/
│   │   └── auth.ts
│   ├── api/
│   │   └── http.ts
│   └── utils/
│       └── storage.ts
└── index.html
```

## 2. 危险代码

### 2.1 v-html XSS（UserProfile.vue）

```vue
<template>
    <div>
        <h1>{{ user.name }}</h1>
        <!-- ❌ 危险：用户简介直接 v-html -->
        <div v-html="user.bio"></div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
const user = ref<any>({})
onMounted(async () => {
    const res = await fetch('/api/user/profile')
    user.value = await res.json()
})
</script>
```

**风险**：后端未净化 `bio` 字段时，XSS 立即触发。

### 2.2 路由守卫缺陷（router/index.ts）

```ts
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        { path: '/', component: () => import('@/views/Dashboard.vue') },
        { path: '/profile/:id', component: () => import('@/views/UserProfile.vue') },
        // ❌ 缺 meta.requiresAuth
        { path: '/admin', component: () => import('@/views/admin/AdminPanel.vue') }
    ]
})

router.beforeEach((to, from, next) => {
    // ❌ 仅前端校验
    if (to.path.startsWith('/admin')) {
        const token = localStorage.getItem('token')
        if (token) {
            next()
        } else {
            next('/login')
        }
    } else {
        next()
    }
})
```

**风险**：
- 后端 `/admin/*` 端点**必须**二次鉴权（仅前端守卫可绕过）
- localStorage 存 token 易被 XSS 窃取

### 2.3 客户端 token 存储（storage.ts）

```ts
// utils/storage.ts
export const tokenStorage = {
    set(token: string) {
        localStorage.setItem('token', token)
        localStorage.setItem('refreshToken', token)
    },
    get() {
        return localStorage.getItem('token')
    },
    clear() {
        localStorage.removeItem('token')
        localStorage.removeItem('refreshToken')
    }
}
```

**风险**：
- 任何 XSS 漏洞 → 永久 token 泄露
- 应使用 httpOnly + Secure + SameSite cookie

### 2.4 fetch 缺 CSRF token（api/http.ts）

```ts
// api/http.ts
export async function http(url: string, options: any = {}) {
    const res = await fetch(url, {
        ...options,
        // ❌ 没带 CSRF token
        credentials: 'include',  // 启用 cookie
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    })
    return res.json()
}
```

**风险**：cookie 鉴权 + 无 CSRF token = 跨站请求伪造。

## 3. React 项目危险代码

### 3.1 dangerouslySetInnerHTML（Article.tsx）

```tsx
import { useState, useEffect } from 'react'

export function Article({ id }: { id: string }) {
    const [content, setContent] = useState('')

    useEffect(() => {
        fetch(`/api/articles/${id}`)
            .then(r => r.json())
            .then(d => setContent(d.content))
    }, [id])

    return (
        <div>
            <h1>{content.title}</h1>
            {/* ❌ 危险 */}
            <div dangerouslySetInnerHTML={{ __html: content.body }} />
        </div>
    )
}
```

### 3.2 href 注入（UserList.tsx）

```tsx
export function UserList({ users }: { users: User[] }) {
    return (
        <ul>
            {users.map(u => (
                <li key={u.id}>
                    {/* ❌ 危险：u.website 可为 javascript: */}
                    <a href={u.website}>{u.name}</a>
                </li>
            ))}
        </ul>
    )
}
```

**风险**：`u.website = "javascript:alert(document.cookie)"` 触发 XSS。

### 3.3 LocalStorage 存 PII（authStore.ts）

```ts
// zustand store
import create from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuth = create(persist(
    (set) => ({
        user: null,
        token: null,
        // ... 全部存 localStorage
    }),
    { name: 'auth' }
))
```

**风险**：localStorage 易被 XSS 窃取。

## 4. Agent 审计流程

### 4.1 模式选择

```
mode: frontend-focused
```

### 4.2 入口定位

```bash
$ python3 scripts/framework_detect.py ./vue3-admin
[OK] profile written to framework_profile.json
     primary_language: javascript
     frameworks: ['vue']
     entry_points: 1
```

### 4.3 危险 sink 扫描

```bash
$ grep -rn "v-html=" src/  # Vue
$ grep -rn "dangerouslySetInnerHTML" src/  # React
$ grep -rn "bypassSecurityTrust" src/  # Angular
$ grep -rn "{@html" src/  # Svelte
$ grep -rn "innerHTML\s*=" src/  # Vanilla
$ grep -rn "localStorage\." src/  # Storage
$ grep -rnE "\beval\s*\(" src/  # eval
$ grep -rn "new Function" src/  # Function ctor
```

输出候选位置 → LLM 逐个判断。

### 4.4 LLM 推理样例

#### Finding: UserProfile.vue v-html

```yaml
finding:
  id: FND-0001
  title: UserProfile.vue 使用 v-html 渲染用户简介，存在存储型 XSS
  file: src/views/UserProfile.vue
  file_line: 6
  call_chain:
    - GET /api/user/profile
    - fetch → response.bio
    - <div v-html="user.bio">
  source: 后端用户简介字段
  sanitization: NONE
  trigger: 任何已登录用户访问 /profile/<id> 即可
  severity: High  (XSS stored)
  cwe: CWE-79
  owasp: A03:2021
  vuln_class: xss-stored
  confidence: Confirmed
  url_or_path: /profile/:id
  parameter: bio
```

修复：
```vue
<template>
    <div>
        <h1>{{ user.name }}</h1>
        <!-- 方案 1: 用纯文本 -->
        <p>{{ user.bio }}</p>

        <!-- 方案 2: 用 DOMPurify 净化 -->
        <div v-html="sanitizedBio"></div>
    </div>
</template>

<script setup lang="ts">
import DOMPurify from 'dompurify'
const sanitizedBio = computed(() => DOMPurify.sanitize(user.value.bio))
</script>
```

#### Finding: router 守卫仅前端校验

```yaml
finding:
  id: FND-0002
  title: router.beforeEach 仅前端校验 /admin，后端必须二次鉴权
  file: src/router/index.ts
  file_line: 23
  severity: Informational  (前端绕过是已知，前提是后端有二次鉴权)
  cwe: CWE-602
  owasp: A01:2021
  note: |
    前端守卫仅 UX 优化，**不可作为唯一防线**。
    后端必须对 /api/admin/* 接口做鉴权（token + 角色）。
```

LLM 在 finding 中明确："这是设计建议，不是漏洞（如果后端已有鉴权）"。

#### Finding: token 存 localStorage

```yaml
finding:
  id: FND-0003
  title: token 存 localStorage，XSS 即可窃取
  file: src/utils/storage.ts
  severity: Medium  (取决于是否有其他 XSS)
  cwe: CWE-1004
  owasp: A07:2021
  vuln_class: info-leak
  note: |
    建议改用 httpOnly + Secure + SameSite=Strict cookie。
    配合 CSP 头禁止 inline script。
```

### 4.5 报告

```bash
$ python3 scripts/render_report.py \
    --findings findings.json \
    --assets assets.json \
    --profile framework_profile.json \
    --output code-audit-report.html \
    --project-name "vue3-admin" \
    --target "./vue3-admin" \
    --mode frontend-focused

[OK] report written to code-audit-report.html
```

## 5. 前端审计的关键点

| 漏洞 | 评级逻辑 |
|---|---|
| v-html / dangerouslySetInnerHTML | 视 source 是否用户可控 → High |
| 路由守卫仅前端 | 提示性，不计 Critical |
| localStorage 存 token | 视有无其他 XSS → Medium |
| href 注入 javascript: | 视 source 是否用户输入 → High |
| innerHTML 拼字符串 | High |
| fetch 缺 CSRF | 视是否 cookie 鉴权 → High |

## 6. 报告样例（节选）

```html
<section id="FND-0001" class="finding severity-High">
  <header class="finding-header">
    <span class="id">FND-0001</span>
    <h3>UserProfile.vue 使用 v-html 渲染用户简介，存在存储型 XSS</h3>
    <span class="badge severity-High">High</span>
    <span class="badge confidence">Confirmed</span>
    <span class="badge cwe">CWE-79</span>
    <span class="badge owasp">A03:2021</span>
    <span class="badge language">vue</span>
  </header>

  <h4>📋 描述</h4>
  <p>UserProfile.vue 第 6 行使用 <code>v-html="user.bio"</code> 直接渲染用户简介。
     该字段来自 <code>GET /api/user/profile</code> 后端响应，未做 HTML 净化。
     攻击者可在个人简介中注入 <code>&lt;script&gt;alert(1)&lt;/script&gt;</code>，
     任何访问该用户主页的用户都会执行恶意脚本。</p>

  <h4>📝 vulnerable code</h4>
  <pre><code class="language-markup">&lt;template&gt;
    &lt;div&gt;
        &lt;h1&gt;{{ user.name }}&lt;/h1&gt;
        &lt;div v-html="user.bio"&gt;&lt;/div&gt;
    &lt;/div&gt;
&lt;/template&gt;</code></pre>

  <h4>🔧 修复建议</h4>
  <h5>方案 1: 改用纯文本插值（推荐）</h5>
  <pre><code class="language-markup">&lt;div&gt;{{ user.bio }}&lt;/div&gt;</code></pre>

  <h5>方案 2: 用 DOMPurify 净化（保留富文本）</h5>
  <pre><code class="language-typescript">import DOMPurify from 'dompurify'
const sanitized = computed(() =&gt; DOMPurify.sanitize(user.value.bio))
// 模板: &lt;div v-html="sanitized"&gt;&lt;/div&gt;</code></pre>

  <h5>方案 3: 后端在写入时净化</h5>
  <pre><code class="language-java">// 服务端: User.bio 字段入库前 sanitize
user.setBio(HtmlUtils.htmlEscape(input.getBio()));</code></pre>
</section>
```
