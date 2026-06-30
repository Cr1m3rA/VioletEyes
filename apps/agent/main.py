"""
VioletEyes-neo Agent Runtime 主入口（spec §7.1）。

通过 stdin/stdout NDJSON 与 api 通信。所有 LLM 调用走 api 中转。
启动：
    python3 main.py
由 apps/api 的 ScanRunnerService.spawn() 拉起。
"""
from __future__ import annotations

import sys
import signal
import threading
from dataclasses import asdict

from protocol import (
    ReadyMessage,
    EventMessage,
    DoneMessage,
    ErrorMessage,
    encode,
    decode,
)


class AgentRuntime:
    """单次 scan 运行的生命周期管理。"""

    def __init__(self) -> None:
        self.scan_run_id: str = ""
        self.code_version_path: str = ""
        self.skill_plan: dict = {}
        self._cancel = threading.Event()

    def run(self) -> None:
        """阻塞 stdin 循环。"""
        signal.signal(signal.SIGTERM, self._on_cancel)
        signal.signal(signal.SIGINT, self._on_cancel)

        self._send(asdict(ReadyMessage()))

        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue
            try:
                msg = decode(line)
            except Exception as e:
                self._send(asdict(ErrorMessage(message=f"invalid json: {e}")))
                continue

            mtype = msg.get("type")
            try:
                if mtype == "init":
                    self._handle_init(msg)
                elif mtype == "llm.call":
                    self._handle_llm_call(msg)
                elif mtype == "tool.call":
                    self._handle_tool_call(msg)
                elif mtype == "cancel":
                    self._on_cancel()
                    break
                else:
                    self._send(asdict(ErrorMessage(message=f"unknown msg type: {mtype}")))
            except Exception as e:
                import traceback

                self._send(
                    asdict(
                        ErrorMessage(
                            message=f"handler error: {e}",
                            stack=traceback.format_exc(),
                        )
                    )
                )

    # ── handlers ──

    def _handle_init(self, msg: dict) -> None:
        self.scan_run_id = msg.get("scan_run_id", "")
        self.code_version_path = msg.get("code_version_path", "")
        self.skill_plan = msg.get("skill_plan", {})
        # TODO Phase 3: 加载 skills、跑 5 阶段流水线
        self._send(
            asdict(
                EventMessage(
                    event_type="phase.start",
                    payload={"phase": "recon"},
                )
            )
        )

    def _handle_llm_call(self, msg: dict) -> None:
        """占位实现：把请求回传给 api 等待结果（实际 LLM 调用在 api 端）。

        真实实现：agent 解析 skill，按阶段构造 system prompt + messages，发起
        一系列 llm.call 请求并处理 tool_calls。每轮 llm.result 包含 LLM 决策。
        """
        # Phase 3 占位
        self._send(
            asdict(
                ErrorMessage(
                    message="llm.call not yet implemented (Phase 3 in progress)",
                )
            )
        )

    def _handle_tool_call(self, msg: dict) -> None:
        """工具调用（Phase 3 实施）。"""
        self._send(
            asdict(
                ErrorMessage(
                    message="tool.call not yet implemented (Phase 3 in progress)",
                )
            )
        )

    # ── helpers ──

    def _send(self, msg: dict) -> None:
        sys.stdout.write(encode(msg) + "\n")
        sys.stdout.flush()

    def _on_cancel(self, *_args) -> None:
        self._cancel.set()
        self._send(
            asdict(
                EventMessage(
                    event_type="run.status",
                    payload={"status": "canceled"},
                )
            )
        )
        self._send(asdict(DoneMessage(summary={"status": "canceled"})))
        sys.exit(0)


if __name__ == "__main__":
    AgentRuntime().run()