"""
NDJSON 协议定义（spec §7.1）。

api → agent（一行 JSON）
agent → api（一行 JSON）

agent **不直接调 LLM**，所有 LLM 调用通过 stdin 发请求，等 stdout 拿结果。
这保证：1) 密钥只在 api 端；2) api 端可观测所有 LLM 调用；3) agent 死掉不丢密钥。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal


# ── api → agent ──


@dataclass
class InitMessage:
    type: Literal["init"] = "init"
    scan_run_id: str = ""
    code_version_path: str = ""
    skill_plan: dict[str, Any] = field(default_factory=dict)
    budget: dict[str, int] = field(default_factory=dict)


@dataclass
class LlmCallMessage:
    type: Literal["llm.call"] = "llm.call"
    request_id: str = ""
    system_prompt: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)
    max_tokens: int = 16384
    temperature: float = 0.2


@dataclass
class ToolCallMessage:
    type: Literal["tool.call"] = "tool.call"
    request_id: str = ""
    name: str = ""
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class CancelMessage:
    type: Literal["cancel"] = "cancel"


# ── agent → api ──


@dataclass
class ReadyMessage:
    type: Literal["ready"] = "ready"


@dataclass
class LlmResultMessage:
    type: Literal["llm.result"] = "llm.result"
    request_id: str = ""
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)  # input/output tokens
    cost_usd: float = 0.0


@dataclass
class ToolResultMessage:
    type: Literal["tool.result"] = "tool.result"
    request_id: str = ""
    result: Any = None
    error: str | None = None


@dataclass
class EventMessage:
    type: Literal["event"] = "event"
    event_type: str = ""  # phase.start / log.line / finding.added / run.status / skill.started / ...
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class DoneMessage:
    type: Literal["done"] = "done"
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorMessage:
    type: Literal["error"] = "error"
    message: str = ""
    stack: str | None = None


# ── 编解码 ──


def encode(msg: dict[str, Any]) -> str:
    return json.dumps(msg, ensure_ascii=False, separators=(",", ":"))


def decode(line: str) -> dict[str, Any]:
    return json.loads(line)