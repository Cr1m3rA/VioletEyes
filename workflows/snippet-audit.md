# Workflow: Snippet Audit（代码片段审计）

> 输入是单段代码（无仓库结构），直接做语言检测 + sink 推理。

## 触发条件

- `mode=snippet`
- 用户在对话中贴了一段代码并问"这里有没有漏洞"

## 步骤

### Step 1: 语言识别

```python
# 用多种信号判断
def detect_language(snippet):
    # 1. 关键字 / 缩进
    if re.search(r"\bpackage\s+[\w.]+;", snippet) and re.search(r"public\s+class", snippet):
        return "java"
    if re.search(r"\bimport\s+[\w.]+;", snippet) and re.search(r"def\s+\w+\s*\(", snippet):
        return "python"
    if re.search(r"<\?php", snippet):
        return "php"
    if re.search(r"\bfunc\s+\w+\s*\(", snippet) and re.search(r"\bpackage\s+", snippet):
        return "go"
    if re.search(r"\bdef\s+\w+", snippet) and re.search(r"\bend\b", snippet):
        return "ruby"
    if re.search(r"\b(public|private)\s+class", snippet) and re.search(r"using\s+System", snippet):
        return "csharp"
    if re.search(r"<\s*template\s*>", snippet) or re.search(r"\bdata\s*:\s*", snippet):
        return "vue"
    if re.search(r"import\s+React", snippet) or re.search(r"from\s+['\"]react", snippet):
        return "react"
    # 2. 用户指定
    # 3. fallback: "plaintext"
```

### Step 2: 调用 sink_detect.py

```bash
# 写入临时文件
cat > /tmp/snippet.<ext> << 'EOF'
<snippet content>
EOF

python3 scripts/sink_detect.py /tmp/snippet.<ext> --json
```

### Step 3: LLM 推理（关键步骤）

**注意**：snippet 没有 import / 调用链上下文，LLM 必须：

1. **推测 source**：基于变量名 / 注释 / 上下文
2. **评估净化**：是否有 escape / 参数化
3. **下浮 confidence**：
   - 无调用链：`confidence ≤ Medium`
   - 无净化证据：标注"需人工确认净化策略"
   - 无路由信息：标注"是否可外部触发未知"
4. **给出建议**：调用方应做什么防护

### Step 4: 报告

```
报告标题: code-audit-report.html (snippet)
封面:
  - 模式: snippet
  - 目标: <inline code>
  - 大小: N 行
banner: ⚠ "代码片段审计 — 仅基于片段内容，缺调用链上下文"
```

每个 finding 额外字段：
```json
{
  "snippet_mode": true,
  "snippet_source": "user_provided",
  "call_chain": [],   // 空数组
  "confidence": "Medium"   // 自动下调
}
```

## 局限性声明

LLM 在 snippet 模式下**无法**保证：
- 是否被路由调用
- 是否在受信任上下文
- 是否有上游净化
- 是否已被禁用但仍存在

snippet 模式产出的 finding **必须**经过人工复核才能作为最终结论。

## 示例输入

```python
@app.route('/search')
def search():
    query = request.args.get('q', '')
    sql = "SELECT * FROM products WHERE name = '" + query + "'"
    result = db.execute(sql).fetchall()
    return render_template('result.html', products=result)
```

LLM 推理：
- sink: `db.execute(sql)` 字符串拼接
- CWE-89
- source: `request.args.get('q')` 用户输入
- 净化: 无
- 路由: `@app.route('/search')` 公开
- confidence: Confirmed（snippet 也能判断）
- severity: High（SQL 注入读）
- remediation: `db.execute("SELECT * FROM products WHERE name = ?", (query,))`
