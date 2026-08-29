"""线性多轮 Session。

Session 保存完整历史；发送给 LLM 的上下文窗口由 ContextManager 另行裁剪，
从而把“长期保存”和“本轮模型输入”两个职责分开。
"""

from __future__ import annotations

import json

from traceforge.llm.messages import LLMResponse
from traceforge.prompts.system_prompt import SYSTEM_PROMPT

from .store import SessionStore


class Session:
    """维护可持久化的完整消息历史。"""

    def __init__(self, store: SessionStore | None = None) -> None:
        self.store = store
        loaded = store.load() if store else []
        self.messages = loaded or [{"role": "system", "content": SYSTEM_PROMPT}]

        # 老版本或损坏历史没有 system message 时自动补齐；
        # 提示词升级后同步刷新首条 system message，避免旧会话继续使用过期策略。
        if self.messages[0].get("role") != "system":
            self.messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
            self._rewrite()
        elif self.messages[0].get("content") != SYSTEM_PROMPT:
            self.messages[0] = {"role": "system", "content": SYSTEM_PROMPT}
            self._rewrite()

    def add_user(self, content: str) -> None:
        self._append({"role": "user", "content": content})

    def add_assistant_response(self, response: LLMResponse) -> None:
        """把模型文本和 tool_calls 保存成标准 Chat Completions 消息。"""
        message: dict = {"role": "assistant", "content": response.content}
        if response.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments, ensure_ascii=False),
                    },
                }
                for call in response.tool_calls
            ]
        self._append(message)

    def add_tool_result(self, tool_call_id: str, name: str, result: str) -> None:
        self._append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": name,
                "content": result,
            }
        )

    def reset(self) -> None:
        """清空历史并恢复初始 system prompt。"""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._rewrite()

    def _append(self, message: dict) -> None:
        self.messages.append(message)
        if self.store:
            self.store.append(message)

    def _rewrite(self) -> None:
        if self.store:
            self.store.rewrite(self.messages)
