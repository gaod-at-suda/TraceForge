"""发送给 LLM 的上下文窗口管理。

V3 不再只按轮次截断：当历史过长时，把旧轮次确定性压缩为摘要，
同时完整保留最近若干轮，避免 tool_call / tool_result 被拆散。
"""

from __future__ import annotations

from traceforge.context import ContextCondenser, estimate_chars


class ContextManager:
    """按完整用户轮次构建模型输入，并控制上下文预算。"""

    def __init__(
        self,
        max_history_turns: int = 8,
        max_context_chars: int = 48000,
        summary_chars: int = 6000,
    ) -> None:
        self.max_history_turns = max(2, int(max_history_turns))
        self.max_context_chars = max(8000, int(max_context_chars))
        self.condenser = ContextCondenser(summary_chars)

    def build(self, messages: list[dict]) -> list[dict]:
        if not messages:
            return []

        system = messages[0] if messages[0].get("role") == "system" else None
        body = messages[1:] if system else messages[:]
        turns = self._group_turns(body)

        # max_history_turns 的语义保持和 V2 一致：先只选最近 N 个完整用户轮次。
        # Condenser 只在“这 N 轮本身仍然过长”时工作，不改变原有窗口边界。
        selected = turns[-self.max_history_turns :]
        direct = self._flatten(system, selected)
        if estimate_chars(direct) <= self.max_context_chars:
            return direct

        # 保留最近 4 轮原文；selected 中更早的部分压缩成第二条 system 摘要。
        recent_count = min(4, len(selected))
        recent = selected[-recent_count:]
        older = selected[:-recent_count]

        result: list[dict] = [system] if system else []
        if older:
            summary = self.condenser.summarize(older)
            if summary:
                result.append(
                    {
                        "role": "system",
                        "content": (
                            "Condensed prior conversation context. "
                            "This is a local deterministic summary, not a new user request:\n"
                            + summary
                        ),
                    }
                )

        for turn in recent:
            result.extend(turn)
        return result

    @staticmethod
    def _group_turns(body: list[dict]) -> list[list[dict]]:
        turns: list[list[dict]] = []
        current: list[dict] = []
        for message in body:
            if message.get("role") == "user":
                if current:
                    turns.append(current)
                current = [message]
            else:
                current.append(message)
        if current:
            turns.append(current)
        return turns

    @staticmethod
    def _flatten(system: dict | None, turns: list[list[dict]]) -> list[dict]:
        result = [system] if system else []
        for turn in turns:
            result.extend(turn)
        return result
