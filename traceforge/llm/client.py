"""大语言模型客户端。

仅使用模型厂商提供的 API 客户端，不使用任何 Agent 框架。
这里采用 OpenAI Python 客户端，因此也可以连接兼容 OpenAI 协议的模型服务。
"""

from __future__ import annotations

from openai import OpenAI

from traceforge.config.settings import Settings

from .parser import parse_response


class LLMClient:
    """封装一次标准的模型调用。"""

    def __init__(self, settings: Settings) -> None:
        client_args = {"api_key": settings.api_key}
        if settings.base_url:
            client_args["base_url"] = settings.base_url

        self.client = OpenAI(**client_args)
        self.model_name = settings.model_name

    def chat(self, messages: list[dict], tools: list[dict] | None = None):
        """向模型发送上下文和可选工具定义，并返回统一响应对象。

        tools=None/[] 时不向厂商 API 发送 tools 字段，用于 Agent 的无工具收尾阶段。
        """
        request: dict = {
            "model": self.model_name,
            "messages": messages,
            "extra_body": {
                "thinking": {
                    "type": "disabled"
                }
            },
        }
        if tools:
            request["tools"] = tools

        response = self.client.chat.completions.create(**request)
        return parse_response(response.choices[0].message)
