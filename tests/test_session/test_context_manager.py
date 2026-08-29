"""上下文窗口按完整用户轮次裁剪测试。"""

from traceforge.agent.context import ContextManager


def test_context_keeps_recent_complete_turns():
    messages = [{"role": "system", "content": "sys"}]
    for i in range(4):
        messages.extend([
            {"role": "user", "content": f"u{i}"},
            {"role": "assistant", "content": f"a{i}"},
        ])

    result = ContextManager(max_history_turns=2).build(messages)
    assert result[0]["role"] == "system"
    assert [m["content"] for m in result[1:]] == ["u2", "a2", "u3", "a3"]
