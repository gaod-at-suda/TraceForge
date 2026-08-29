"""结构化工具执行结果。

ToolRegistry 采用 Never-Throw 边界：无论成功还是失败，都返回 ToolResult，
让 Agent 可以把错误作为观察结果反馈给 LLM，而不是直接崩溃。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """统一描述本地工具的一次执行结果。"""

    success: bool
    output: str = ""
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_model_text(self) -> str:
        """转换为反馈给 LLM 的文本观察。"""
        if self.success:
            return self.output or "OK"
        return f"TOOL_ERROR: {self.error or '未知工具错误'}"
