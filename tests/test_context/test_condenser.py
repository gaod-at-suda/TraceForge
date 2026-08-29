"""上下文压缩测试。"""

from traceforge.agent.context import ContextManager


def test_context_condenses_old_turns():
    messages = [{"role": "system", "content": "system"}]
    for i in range(10):
        messages.extend(
            [
                {"role": "user", "content": f"task {i} " + "x" * 3000},
                {"role": "assistant", "content": f"done {i}"},
            ]
        )

    manager = ContextManager(
        max_history_turns=5,
        max_context_chars=8000,
        summary_chars=1500,
    )
    result = manager.build(messages)

    assert result[0]["role"] == "system"
    assert any(
        msg["role"] == "system" and "Condensed prior conversation" in msg["content"]
        for msg in result[1:]
    )
    assert result[-2]["content"].startswith("task 9")


def test_context_limits_single_long_tool_task_without_splitting_tool_pairs():
    from traceforge.context import estimate_chars

    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "请检查项目并修复失败测试"},
    ]
    for index in range(10):
        call_id = f"call-{index}"
        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path":"sample.py"}',
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": "read_file",
                    "content": "x" * 5000,
                },
            ]
        )

    manager = ContextManager(
        max_history_turns=8,
        max_context_chars=12000,
        summary_chars=1800,
    )
    result = manager.build(messages)

    assert estimate_chars(result) <= 12000
    assert any(
        message.get("role") == "user" and "修复失败测试" in message.get("content", "")
        for message in result
    )

    visible_call_ids = {
        call["id"]
        for message in result
        if message.get("role") == "assistant"
        for call in message.get("tool_calls", [])
    }
    tool_call_ids = {
        message["tool_call_id"]
        for message in result
        if message.get("role") == "tool"
    }
    assert tool_call_ids
    assert tool_call_ids <= visible_call_ids
    assert "call-9" in tool_call_ids
