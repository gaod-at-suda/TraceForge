"""LLM 与 Agent 之间的统一数据结构。

Agent 核心逻辑不直接依赖某个模型厂商的原始 Response 对象，
使上层 Agent Loop 与具体 OpenAI-compatible 模型响应格式解耦。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """模型请求执行的一次工具调用。"""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """标准化后的模型响应。"""

    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_message: Any = None
