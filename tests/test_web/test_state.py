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


class FailingAgent(FakeAgent):
    def run(self, task):
        raise RuntimeError("boom")


def test_web_state_surfaces_unexpected_agent_error():
    state = WebState(FailingAgent(), InMemoryEventStore())
    assert state.start_task("hello") is True

    for _ in range(100):
        if not state.status()["running"]:
            break
        time.sleep(0.005)

    status = state.status()
    assert status["running"] is False
    assert status["result"] is not None
    assert status["result"]["success"] is False
    assert "Web 后台任务异常" in status["result"]["message"]


class MutatingAgent(FakeAgent):
    """模拟一次建立 Checkpoint 并修改工作区的成功 Agent 任务。"""

    def __init__(self, root, manager, event_bus):
        super().__init__()
        self.root = root
        self.manager = manager
        self.event_bus = event_bus

    def run(self, task):
        checkpoint = self.manager.create()
        run_id = "restore-run"
        self.event_bus.emit(
            "run_started",
            run_id,
            data={
                "task": task,
                "mode": "auto",
                "checkpoint_enabled": checkpoint.enabled,
                "checkpoint_revision": checkpoint.revision,
                "checkpoint_reason": checkpoint.reason,
            },
        )
        (self.root / "a.txt").write_text("agent change\n", encoding="utf-8")
        (self.root / "new.txt").write_text("created by agent\n", encoding="utf-8")
        self.event_bus.emit(
            "file_changed",
            run_id,
            step=1,
            data={"path": "a.txt", "diff": "-base\n+agent change"},
        )
        self.event_bus.emit("run_finished", run_id, step=1, data={"message": "done"})
        return AgentResult(True, "done", 1, run_id)


def _init_restore_repo(tmp_path):
    from pathlib import Path
    import subprocess

    from traceforge.events import EventBus
    from traceforge.git import GitCheckpointManager
    from traceforge.workspace.workspace import Workspace

    root = Path(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / "a.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-q", "-m", "base",
        ],
        cwd=root,
        check=True,
    )
    store = InMemoryEventStore()
    bus = EventBus()
    bus.subscribe(store.on_event)
    manager = GitCheckpointManager(Workspace(root))
    agent = MutatingAgent(root, manager, bus)
    return root, store, bus, manager, agent


def _wait_for_web_state(state):
    for _ in range(100):
        if not state.status()["running"]:
            return
        time.sleep(0.005)
    raise AssertionError("WebState task did not finish in time")


def test_web_state_can_restore_latest_agent_changes(tmp_path):
    root, store, bus, manager, agent = _init_restore_repo(tmp_path)
    state = WebState(agent, store, manager, bus)

    assert state.start_task("change files") is True
    _wait_for_web_state(state)
    assert state.status()["restore"]["available"] is True

    ok, message = state.restore_last_run()
    assert ok is True
    assert "已恢复" in message
    assert (root / "a.txt").read_text(encoding="utf-8") == "base\n"
    assert not (root / "new.txt").exists()
    assert agent.reset_count == 1
    assert state.status()["restore"]["used"] is True

    event_types = [item["event_type"] for item in store.after(0)]
    assert "manual_restore_started" in event_types
    assert "manual_restore_finished" in event_types


def test_web_state_refuses_restore_after_new_manual_change(tmp_path):
    root, store, bus, manager, agent = _init_restore_repo(tmp_path)
    state = WebState(agent, store, manager, bus)

    assert state.start_task("change files") is True
    _wait_for_web_state(state)
    assert state.status()["restore"]["available"] is True

    (root / "a.txt").write_text("manual change after agent\n", encoding="utf-8")
    ok, message = state.restore_last_run()
    assert ok is False
    assert "人工修改" in message
    assert (root / "a.txt").read_text(encoding="utf-8") == "manual change after agent\n"
    assert (root / "new.txt").exists()
