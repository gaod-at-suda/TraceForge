"""工具步数耗尽后的无工具收尾测试。"""

from traceforge.agent.context import ContextManager
from traceforge.agent.loop import AgentLoop
from traceforge.config.settings import Settings
from traceforge.events import EventBus, InMemoryEventStore
from traceforge.git import GitCheckpoint
from traceforge.llm.messages import LLMResponse, ToolCall
from traceforge.session import Session
from traceforge.tools.result import ToolResult
from traceforge.verification import VerificationResult


class FinalizingLLM:
    def __init__(self):
        self.calls = 0
        self.tools_seen = []

    def chat(self, messages, tools=None):
        self.calls += 1
        self.tools_seen.append(tools)
        if self.calls == 1:
            return LLMResponse(
                content="继续修改",
                tool_calls=[ToolCall("call-1", "fake_write", {"path": "a.py"})],
            )
        return LLMResponse(content="任务已完成并通过验证。", tool_calls=[])


class MutatingRegistry:
    schemas = [{"type": "function", "function": {"name": "fake_write"}}]

    def __init__(self):
        self.mutation_count = 0

    def reset_run_state(self):
        self.mutation_count = 0

    def execute(self, name, arguments):
        self.mutation_count += 1
        return ToolResult(True, "written", metadata={"mutation": True, "path": "a.py"})


class PassingVerifier:
    def __init__(self):
        self.calls = 0

    def verify(self):
        self.calls += 1
        return VerificationResult(True, True, "pytest -q", "test", 0, "1 passed")


class FakeCheckpointManager:
    def create(self):
        return GitCheckpoint(False, reason="test")


def test_step_limit_gets_one_tool_free_finalization(tmp_path):
    settings = Settings(
        api_key="x",
        model_name="fake",
        base_url=None,
        max_steps=1,
        command_timeout=5,
        max_tool_output=1000,
        max_history_turns=4,
        max_context_chars=48000,
        condensed_summary_chars=6000,
        verification_retries=1,
        runtime_dir=tmp_path / "runtime",
        agent_mode="auto",
    )
    llm = FinalizingLLM()
    verifier = PassingVerifier()
    bus = EventBus()
    store = InMemoryEventStore()
    bus.subscribe(store.on_event)

    loop = AgentLoop(
        llm=llm,
        tool_registry=MutatingRegistry(),
        settings=settings,
        event_bus=bus,
        context_manager=ContextManager(4),
        verifier=verifier,
        checkpoint_manager=FakeCheckpointManager(),
    )

    result = loop.run(Session(), "修改并测试")

    assert result.success is True
    assert result.steps == 1
    assert llm.calls == 2
    assert llm.tools_seen[0]
    assert llm.tools_seen[1] is None
    assert verifier.calls == 1
    event_types = [event["event_type"] for event in store.after(0)]
    assert "finalization_started" in event_types
    assert "finalization_finished" in event_types
    assert "run_finished" in event_types
