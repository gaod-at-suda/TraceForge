"""大语言模型客户端。

仅使用模型厂商提供的 API 客户端，不使用任何 Agent 框架。
核心调用遵循 OpenAI-compatible Chat Completions / Tool Calling 协议；
厂商特有参数仅在客户端适配层按需加入，不影响 Agent Loop 与工具执行逻辑。
"""

from __future__ import annotations

from traceforge.config.settings import Settings

from .parser import parse_response


class LLMClient:
    """封装一次标准模型调用，并隔离模型服务的兼容性差异。"""

    def __init__(self, settings: Settings) -> None:
        # 延迟导入第三方模型客户端，使不涉及线上调用的本地单元测试保持轻量。
        from openai import OpenAI

        client_args = {"api_key": settings.api_key}
        if settings.base_url:
            client_args["base_url"] = settings.base_url

        self.client = OpenAI(**client_args)
        self.model_name = settings.model_name
        self.base_url = settings.base_url or ""

    def chat(self, messages: list[dict], tools: list[dict] | None = None):
        """发送上下文和可选工具定义，并返回 TraceForge 统一响应对象。

        ``tools=None`` 或空列表时不发送 tools 字段，用于 Agent 的无工具最终收尾。
        """
        request = self._build_request(messages, tools)
        response = self.client.chat.completions.create(**request)
        return parse_response(response.choices[0].message)

    def _build_request(
        self,
        messages: list[dict],
        tools: list[dict] | None,
    ) -> dict:
        """构造厂商请求；Agent 核心逻辑不感知服务端专有参数。"""
        request: dict = {
            "model": self.model_name,
            "messages": messages,
        }
        if tools:
            request["tools"] = tools

        # DeepSeek 的部分模型支持 thinking 扩展。TraceForge 当前演示关闭该模式，
        # 以保持 Tool Calling 行为稳定；其他 OpenAI-compatible 服务不携带此专有字段。
        if self._uses_deepseek_extensions():
            request["extra_body"] = {
                "thinking": {
                    "type": "disabled",
                }
            }
        return request

    def _uses_deepseek_extensions(self) -> bool:
        value = f"{self.model_name} {self.base_url}".lower()
        return "deepseek" in value
