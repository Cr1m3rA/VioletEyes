# apps/api 报告模板引用说明

> VioletEyes-neo 的 HTML 报告**直接复用** VioletEyes Skill v1.2 的 Jinja2 模板，**不复制**。原因：复制会导致两份模板漂移；VioletEyes 模板本身是稳定资产，复制无收益。

## 引用方式

`apps/api` 启动时读取环境变量 `TEMPLATES_DIR`，默认 `<repo-root>/templates`：

```typescript
// apps/api/src/report/templates-path.ts
import path from 'node:path';

const repoRoot = path.resolve(__dirname, '../../../..'); // apps/api/src/ → repo root
export const TEMPLATES_DIR = process.env.TEMPLATES_DIR ?? path.join(repoRoot, 'templates');
```

## 模板清单（与 VioletEyes 一致）

- `base.html.j2` — 主骨架（Cover + Sticky header + findings index）
- `finding.html.j2` — finding 卡片（含 CallChainTabs 双 Tab）
- `partials/*.j2` — cover / summary / dashboard / framework / findings_index / dependency_cve / appendix / disclaimer
- `inline/*` — Tailwind v4 / Alpine / Chart / Mermaid / Prism（17 个语言）全部内联，离线可用
- `base.css` — 自定义 CSS（紫罗兰主题 + 严重度色 + 打印样式）

## 渲染流程

1. apps/agent 子进程被 spawn
2. agent 接收 `<scanRunId, codeVersionPath, findings, cost, smartDecision>` JSON
3. agent 调 `scripts/render_report.py`（从 VioletEyes 迁入 apps/agent/scripts/）
4. Python Jinja2 渲染 `templates/base.html.j2` → `<storage>/reports/<runId>/code-audit-report.html`

## 修改注意

- **修改 VioletEyes 模板会影响 Skill 与 Platform 两端**，改前必须与 Skill 维护者同步
- 如需 Platform 专属模板（如新增"成本"卡片），建议复制一份到 `apps/api/templates-overrides/` 并在配置里覆盖路径