"""确定性的历史压缩器。

不额外调用 LLM，而是提取旧轮次中的任务、工具名称、错误和最终文本，
生成小型摘要，避免老的源码全文和日志长期占据上下文。
"""

from __future__ import annotations


class ContextCondenser:
    """把较旧完整轮次压缩为可读文本摘要。"""

    def __init__(self, max_chars: int = 6000) -> None:
        self.max_chars = max(1000, int(max_chars))

    def summarize(self, turns: list[list[dict]]) -> str:
        """对旧轮次做确定性摘要。"""
        sections: list[str] = []

        for index, turn in enumerate(turns, start=1):
            items: list[str] = []
            for message in turn:
                role = message.get("role")
                if role == "user":
                    items.append("用户: " + self._clip(message.get("content", ""), 500))
                elif role == "assistant":
                    content = message.get("content") or ""
                    if content:
                        items.append("助手: " + self._clip(content, 350))
                    calls = message.get("tool_calls") or []
                    if calls:
                        names = [
                            call.get("function", {}).get("name", "?")
                            for call in calls
                        ]
                        items.append("调用工具: " + ", ".join(names))
                elif role == "tool":
                    name = message.get("name", "tool")
                    content = str(message.get("content", ""))
                    if "TOOL_ERROR" in content or "exit_code:" in content:
                        items.append(
                            f"{name}结果: " + self._clip(content, 300)
                        )
                    else:
                        items.append(f"{name}结果: 已获得本地观察结果")

            if items:
                sections.append(
                    f"[历史轮次 {index}]\n" + "\n".join(items)
                )
            if len("\n\n".join(sections)) >= self.max_chars:
                break

        summary = "\n\n".join(sections)
        return self._clip(summary, self.max_chars)

    @staticmethod
    def _clip(text: str, limit: int) -> str:
        text = str(text).strip()
        if len(text) <= limit:
            return text
        return text[:limit] + "...[摘要截断]"
