"""WebState 后台任务与会话重置基础测试。"""

import time

from traceforge.agent.result import AgentResult
from traceforge.events.store import InMemoryEventStore
from traceforge.web.state import WebState


class FakeAgent:
    """不调用真实 LLM 的测试 Agent。"""

    def __init__(self):
        self.reset_count = 0

    def run(self, task):
        return AgentResult(True, f"done: {task}", 1, "fake-run")

    def reset_session(self):
        self.reset_count += 1


def test_web_state_runs_task_and_resets():
    agent = FakeAgent()
    state = WebState(agent, InMemoryEventStore())
    assert state.start_task("hello") is True

    for _ in range(100):
        if not state.running:
            break
        time.sleep(0.005)

    assert state.latest_result is not None
    assert state.latest_result.success is True
    assert state.reset_session() is True
    assert agent.reset_count == 1
