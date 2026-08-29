"""ContextManager 基础测试。"""

from traceforge.agent.context import ContextManager


def test_context_preserves_system_message():
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "修复 bug"},
    ]
    result = ContextManager(8).build(messages)
    assert result[0]["role"] == "system"
    assert result[1]["content"] == "修复 bug"
