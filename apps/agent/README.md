# apps/agent — VioletEyes-neo Agent Runtime

> Python 实现的扫描 agent 子进程（spec §7）。

## 角色

- 由 `apps/api` 通过 `child_process.spawn('python3', ['main.py'])` 拉起
- 通过 stdin/stdout **NDJSON 协议**与 api 通信
- **不直接调 LLM** —— 所有 LLM 调用通过 stdin 发请求，等 stdout 拿结果
- 沙箱运行（filesystem/network/exec 限制；Phase 2 实施）

## 协议

详见 `protocol.py`。两类消息：

```
api → agent：{type: "init"} / {type: "llm.call"} / {type: "tool.call"} / {type: "cancel"}
agent → api：{type: "ready"} / {type: "llm.result"} / {type: "tool.result"} / {type: "event"} / {type: "done"} / {type: "error"}
```

## 启动（开发期独立调试）

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 main.py
```

## 当前状态

- ✅ NDJSON 协议定义（`protocol.py`）
- ✅ 主循环骨架（`main.py`）
- ✅ Cancel 信号处理
- ⏳ Phase 3：5 阶段流水线 + skill 加载 + tool 执行
- ⏳ Phase 4：Jinja2 报告渲染（迁自 VioletEyes `scripts/render_report.py`）

## 相关文件

- `protocol.py` — NDJSON 协议 dataclass + 编解码
- `main.py` — AgentRuntime 主类
- `requirements.txt` — Python 依赖（仅 jinja2 + pyyaml + pydantic）