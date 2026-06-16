# Workflow: API Audit（API 专项审计）

> 聚焦 HTTP API 入口（Controller / Router / Handler），对每个端点做深度审计。

## 触发条件

- `mode=api-focused`
- 适合 REST / GraphQL / WebSocket API 项目

## 步骤

### Step 1: 完整路由表抽取

不仅读入口文件，还**深度扫描**所有 controller / router / handler：

```python
# Agent 任务：
# 1. 列出 src/**/*Controller*.* (按语言)
# 2. 列出 src/**/*router*.* / *routes*.* / *handler*.*
# 3. 解析每个文件，提取所有路由定义
# 4. 输出 routes.json
```

### Step 2: 路由表交叉污染检查

对每个路由：
- HTTP 方法
- 路径参数
- Query 参数
- Body schema
- 鉴权注解 / 中间件
- 调用的 Service / Repository
- 是否校验 owner / 角色
- 是否限速

### Step 3: 重点审计

优先审计：
1. **写操作**（POST / PUT / DELETE / PATCH）—— 业务逻辑、IDOR、Mass Assignment
2. **敏感读**（GET /user/{id} / GET /order/{id}）—— IDOR
3. **文件操作**（上传 / 下载）—— 路径遍历、文件类型绕过
4. **外部输入点**（搜索 / 排序 / 分页）—— SQLi / NoSQLi

跳过：
- 纯静态资源路由
- 健康检查 / 监控端点
- 内部后台 API（已认证 + 限速）

### Step 4: OpenAPI / Swagger 对照

如果有 `openapi.yaml` / `swagger.json`：
- 对照实际实现与文档
- 标记文档缺失的端点
- 标记文档中已声明但未实现的端点

### Step 5: 报告

```
报告标题: code-audit-report.html (api-focused)
封面:
  - 模式: api-focused
  - HTTP 端点: N
  - 鉴权覆盖: X/N
  - 重点审计: 写操作 / 敏感读 / 文件操作
banner: "🎯 API-focused audit — 重点审计 HTTP 入口"
```

## 输出

- `routes.json` — 完整路由表
- `findings.json` — 漏洞
- `api-coverage.json` — 鉴权覆盖情况
- `code-audit-report.html` — 报告

## 不适用：第三方依赖 CVE 扫描（V1.2）

API 专项默认在 `full-audit` 阶段已完成依赖扫描。如需独立再跑：
```bash
python3 scripts/cve_lookup.py <repo_root> --output dep_cve.json
```
