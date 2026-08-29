"""Session 持久化测试。"""

from traceforge.session import Session, SessionStore


def test_session_persists_and_resets(tmp_path):
    store = SessionStore(tmp_path / "session.jsonl")
    session = Session(store)
    session.add_user("第一轮")

    restored = Session(store)
    assert any(m.get("content") == "第一轮" for m in restored.messages)

    restored.reset()
    assert len(restored.messages) == 1
    assert restored.messages[0]["role"] == "system"
