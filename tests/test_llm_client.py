"""模型客户端请求参数隔离测试，不发起真实网络请求。"""

from traceforge.llm.client import LLMClient


def _client(model_name: str, base_url: str = "") -> LLMClient:
    client = LLMClient.__new__(LLMClient)
    client.model_name = model_name
    client.base_url = base_url
    return client


def test_openai_compatible_request_has_no_deepseek_extension():
    client = _client("gpt-4.1-mini", "https://api.openai.com/v1")
    request = client._build_request([{"role": "user", "content": "hello"}], None)

    assert request["model"] == "gpt-4.1-mini"
    assert "extra_body" not in request
    assert "tools" not in request


def test_deepseek_request_adds_thinking_compatibility_parameter():
    client = _client("deepseek-v4-flash", "https://api.deepseek.com")
    tools = [{"type": "function", "function": {"name": "read_file"}}]
    request = client._build_request([{"role": "user", "content": "hello"}], tools)

    assert request["tools"] == tools
    assert request["extra_body"] == {"thinking": {"type": "disabled"}}
