# Workflow: Incremental Audit（增量审计）

> 只审计 diff 变更部分，适合 PR review 场景。

## 触发条件

- `mode=incremental` 或 `mode=diff`
- 输入含 `base_commit` / `head_commit` 或 PR patch

## 步骤

### Step 1: 获取 diff

```bash
# Git 模式
git -C <repo> diff <base_commit> <head_commit> > /tmp/changes.diff
git -C <repo> diff --name-only <base_commit> <head_commit> > /tmp/changed_files.txt

# PR patch 模式
# 用户已提供 patch 文件
```

### Step 2: 解析 diff 涉及文件

LLM 解析 `changed_files.txt`：
- 过滤删除的文件
- 过滤 `*.md` / `*.lock` / lock 文件
- 保留修改的源文件 + 新增的源文件

### Step 3: 浅层上下文读取

对每个变更文件，读取**变更行 ± 30 行**上下文，**不读整个文件**（节省 token）。

LLM 重点关注：
- 变更是否引入新的 sink
- 变更是否移除防护（删除 `htmlspecialchars` 等）
- 变更是否引入了新的依赖

### Step 4: 调用链补全

对每个 finding 候选，**有限**追溯调用链：
- 同文件内的 caller/callee（用 `grep` 找函数名）
- 跨文件只追 1-2 层，避免爆炸

### Step 5: 报告

报告 `mode=incremental` / `base_commit=...` / `head_commit=...`，附"未变更的潜在风险"清单（可选）。

## 输出格式

```json
{
  "mode": "incremental",
  "base_commit": "abc1234",
  "head_commit": "def5678",
  "changed_files_count": 12,
  "findings": [...],
  "introduced_vulns": [
    {"id": "FND-0001", "introduced_in": "abc1234..def5678"}
  ]
}
```

## 报告样例

```
报告标题: code-audit-report.html (incremental)
封面:
  - 模式: incremental
  - 基线: abc1234
  - HEAD: def5678
  - 变更文件: 12
  - 新增漏洞: 3
banner: "🔄 Incremental audit — only diff between abc1234 and def5678 is analyzed"
```
