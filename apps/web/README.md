# apps/web — VioletEyes-neo 前端

> React + Vite + Tailwind v4 + Zustand + TanStack Query + Radix UI（spec §2.2）

## 启动

```bash
pnpm dev        # http://localhost:5173
pnpm build      # 生产构建
pnpm test       # vitest
```

需要 api 端在 http://localhost:3030 运行（vite proxy 已配）。

## 当前状态

- ✅ 完整路由表 + 全局 Header + 登录页（紫光背景 + 毛玻璃表单）
- ✅ Logo / Cover / SeverityBadge / SeverityBar 等 VioletEyes 视觉组件
- ✅ Auth store（access token 内存 + refresh HttpOnly）
- ✅ API 客户端（401 silent refresh）
- ⏳ Phase 1：项目 CRUD + 代码版本上传
- ⏳ Phase 2：Skill 上传 / 审核 / 启用
- ⏳ Phase 3：扫描实时进度（WebSocket）+ Skill 执行卡片
- ⏳ Phase 4：报告页（嵌入 HTML）+ Chart.js + Mermaid
- ⏳ Phase 5：漏洞库趋势 / Agent Trace

## 视觉一致性

设计 token 在 `packages/report-theme/tailwind-preset.js` 与 `tokens.css`。前端 import：

```css
/* index.css 顶部 */
@import '@violeteyes/report-theme/tokens.css';
@import 'tailwindcss';
```

颜色 / 字体 / 严重度色 / Cover 渐变 **与 VioletEyes v1.2 报告严格一致**。