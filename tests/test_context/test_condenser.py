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
