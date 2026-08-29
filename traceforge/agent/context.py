"""发送给 LLM 的上下文窗口管理。

Session 始终保存完整消息历史；ContextManager 只负责构造本次模型调用所需的输入窗口。
当历史超过预算时，较旧内容会被本地确定性摘要替代，同时以原子块形式保留最近的
Assistant Tool Call 与对应 Tool Result，避免产生不完整的工具调用上下文。
"""

from __future__ import annotations

from traceforge.context import ContextCondenser, estimate_chars


class ContextManager:
    """在字符预算内构建稳定、结构完整的模型输入。"""

    _SUMMARY_PREFIX = (
        "Condensed prior conversation context. "
        "This is a local deterministic summary, not a new user request:\n"
    )

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
        """返回发送给模型的上下文，不修改 Session 中保存的完整历史。"""
        if not messages:
            return []

        system = messages[0] if messages[0].get("role") == "system" else None
        body = messages[1:] if system else messages[:]
        turns = self._group_turns(body)

        # 先按用户轮次限制历史范围；在正常规模下直接保留原始消息，避免不必要的信息损失。
        selected_turns = turns[-self.max_history_turns :]
        direct = self._flatten(system, selected_turns)
        if estimate_chars(direct) <= self.max_context_chars:
            return direct

        return self._build_budgeted(system, selected_turns)

    def _build_budgeted(
        self,
        system: dict | None,
        turns: list[list[dict]],
    ) -> list[dict]:
        """在单个长任务产生大量工具输出时继续执行第二级预算控制。

        最近消息按“原子执行块”保留：带 tool_calls 的 assistant 消息与紧随其后的
        tool 结果始终一起保留或一起压缩，不会留下孤立的 Tool Result。
        """
        body = [message for turn in turns for message in turn]
        blocks = self._group_atomic_blocks(body)
        if not blocks:
            return [system] if system else []

        latest_user_block = self._latest_user_block_index(blocks)
        summary_reserve = min(
            self.condenser.max_chars + 400,
            max(1000, self.max_context_chars // 4),
        )

        system_messages = [system] if system else []
        system_size = estimate_chars(system_messages)
        recent_budget = max(0, self.max_context_chars - system_size - summary_reserve)

        kept: set[int] = set()
        if latest_user_block is not None:
            kept.add(latest_user_block)

        # 从最新执行结果向前保留完整原子块；最新用户消息作为任务锚点单独保证保留。
        for index in range(len(blocks) - 1, -1, -1):
            if index in kept:
                continue
            candidate = sorted((*kept, index))
            candidate_messages = [
                message
                for block_index in candidate
                for message in blocks[block_index]
            ]
            if estimate_chars(candidate_messages) <= recent_budget:
                kept.add(index)

        omitted = [
            blocks[index]
            for index in range(len(blocks))
            if index not in kept
        ]
        recent = [
            message
            for index in range(len(blocks))
            if index in kept
            for message in blocks[index]
        ]

        result: list[dict] = list(system_messages)
        if omitted:
            summary = self.condenser.summarize(omitted)
            if summary:
                result.append(
                    {
                        "role": "system",
                        "content": self._SUMMARY_PREFIX + summary,
                    }
                )
        result.extend(recent)

        # 由于 JSON 序列化本身存在少量结构开销，最后再收紧摘要，确保常规情况下不越过配置预算。
        return self._trim_summary_to_budget(result)

    def _trim_summary_to_budget(self, messages: list[dict]) -> list[dict]:
        if estimate_chars(messages) <= self.max_context_chars:
            return messages

        summary_index = next(
            (
                index
                for index, message in enumerate(messages)
                if message.get("role") == "system"
                and str(message.get("content", "")).startswith(self._SUMMARY_PREFIX)
            ),
            None,
        )
        if summary_index is None:
            return messages

        summary_message = dict(messages[summary_index])
        content = str(summary_message.get("content", ""))
        over = estimate_chars(messages) - self.max_context_chars
        keep = max(len(self._SUMMARY_PREFIX), len(content) - over - 128)
        summary_message["content"] = content[:keep]
        if keep < len(content):
            summary_message["content"] += "\n...[摘要按上下文预算截断]"

        trimmed = list(messages)
        trimmed[summary_index] = summary_message

        # 极端情况下摘要已无可裁剪内容，则直接移除摘要；完整 Session 仍保留在本地持久化历史中。
        if estimate_chars(trimmed) > self.max_context_chars:
            trimmed.pop(summary_index)
        return trimmed

    @staticmethod
    def _group_turns(body: list[dict]) -> list[list[dict]]:
        """按 user 消息切分长期会话轮次。"""
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
    def _group_atomic_blocks(messages: list[dict]) -> list[list[dict]]:
        """把 assistant tool_calls 与其连续 Tool Result 组合为不可拆分的执行块。"""
        blocks: list[list[dict]] = []
        index = 0
        while index < len(messages):
            message = messages[index]
            block = [message]
            index += 1

            if message.get("role") == "assistant" and message.get("tool_calls"):
                while index < len(messages) and messages[index].get("role") == "tool":
                    block.append(messages[index])
                    index += 1

            blocks.append(block)
        return blocks

    @staticmethod
    def _latest_user_block_index(blocks: list[list[dict]]) -> int | None:
        for index in range(len(blocks) - 1, -1, -1):
            if any(message.get("role") == "user" for message in blocks[index]):
                return index
        return None

    @staticmethod
    def _flatten(system: dict | None, turns: list[list[dict]]) -> list[dict]:
        result = [system] if system else []
        for turn in turns:
            result.extend(turn)
        return result
