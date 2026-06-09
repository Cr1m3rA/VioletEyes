# Workflow: Full Audit（完整仓库审计）

> 默认工作流。从仓库根目录开始，5 阶段流水线。

## 触发条件

- 用户输入：`/audit <repo_path>` 或 `请审计 <repo_path>`
- `mode=full`（默认）

## 步骤

### Step 1: 准备

```bash
# 验证路径
test -d <repo_path> || (git clone <url> <repo_path> || unzip <archive> -d <repo_path>)

# 构建文件树索引
python3 scripts/tree_index.py <repo_path> --depth 3 --output tree.json
```

### Step 2: 框架识别

```bash
python3 scripts/framework_detect.py <repo_path> --output framework_profile.json
```

LLM 读取 `framework_profile.json`，决定后续读取策略。

### Step 3: 入口定位

按 `signatures/entry-point-patterns.md` 在仓库内找入口：
- 读 `framework_profile.json` 的 `entry_points`
- 补充扫描：
  - Spring: 所有 `@Controller` / `@RestController` 类
  - Django: 所有 `urls.py`
  - Express: 所有 `app.get/post/put/delete` 调用
  - 等等

输出 `assets.json`（仅路由表）。

### Step 4: 步进式读取

LLM 维护 read_queue：
```
queue = [entry_points...] + [config_files...]
```

每读一个文件：
1. 调用 `python3 scripts/sink_detect.py <file> --json` 拿到候选 sink
2. LLM 推理：
   - sink 是否可达？
   - 是否有净化？
   - 调用链可追溯到入口？
3. 决定：
   - 入队 `import` 涉及的新文件
   - 写入 finding / candidate

### Step 5: 报告

```bash
python3 scripts/render_report.py \
    --findings findings.json \
    --assets assets.json \
    --profile framework_profile.json \
    --execution-log execution.log \
    --output code-audit-report.html \
    --project-name "<name>" \
    --target "<repo_path>" \
    --mode full
```

## 输出

- `findings.json` — 漏洞清单
- `assets.json` — 代码资产
- `framework_profile.json` — 框架画像
- `execution.log` — 步进日志
- `code-audit-report.html` — HTML 报告

## 自检

生成报告前：
- [ ] framework_profile.json 非空
- [ ] assets.json 至少 1 个 HTTP 入口（除非是纯库）
- [ ] findings.json 中每条 finding 有 file_path + line
- [ ] execution.log 不含异常堆栈（仅含正常决策日志）

## 异常处理

| 异常 | 处理 |
|---|---|
| 仓库 > 5GB | 仅做 manifest + 顶层结构粗扫，标 partial=true |
| 无 manifest | 用扩展名比例 + 关键文件启发式 |
| 找不到入口 | 扫所有 *Controller* / *router* / *handler* 命名的文件 |
| token 预算耗尽 | 立即停止扩张，已收 finding 出报告，标 partial=true |
