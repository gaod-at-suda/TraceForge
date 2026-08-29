"""模型输出解析。

把 OpenAI 兼容接口返回的 tool_calls 解析为 TraceForge 自己的数据结构。
"""

from __future__ import annotations

import json

from .messages import LLMResponse, ToolCall


def parse_response(message) -> LLMResponse:
    """解析模型返回消息。"""
    parsed_calls: list[ToolCall] = []

    for call in getattr(message, "tool_calls", None) or []:
        raw_arguments = call.function.arguments or "{}"
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError:
            arguments = {"__raw_arguments__": raw_arguments}

        parsed_calls.append(
            ToolCall(
                id=call.id,
                name=call.function.name,
                arguments=arguments,
            )
        )

    return LLMResponse(
        content=getattr(message, "content", None),
        tool_calls=parsed_calls,
        raw_message=message,
    )
