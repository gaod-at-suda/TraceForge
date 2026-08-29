"""Agent Loop 使用 FakeLLM 的控制逻辑测试。"""

from traceforge.agent.context import ContextManager
from traceforge.agent.loop import AgentLoop
from traceforge.config.settings import Settings
from traceforge.events import EventBus
from traceforge.git import GitCheckpoint
from traceforge.llm.messages import LLMResponse
from traceforge.session import Session


class FakeLLM:
    def chat(self, messages, tools):
        return LLMResponse(content="任务完成", tool_calls=[])


class FakeRegistry:
    schemas = []
    mutation_count = 0

    def reset_run_state(self):
        self.mutation_count = 0

    def execute(self, name, arguments):
        raise AssertionError("本测试不应执行工具")


class FakeVerifier:
    def verify(self):
        raise AssertionError("没有文件修改时不应触发验证")


class FakeCheckpointManager:
    def create(self):
        return GitCheckpoint(False, reason="test")


def make_settings(tmp_path):
    return Settings(
        api_key="test",
        model_name="fake",
        base_url=None,
        max_steps=3,
        command_timeout=5,
        max_tool_output=1000,
        max_history_turns=4,
        max_context_chars=48000,
        condensed_summary_chars=6000,
        verification_retries=2,
        runtime_dir=tmp_path / "runtime",
        agent_mode="auto",
    )


def test_agent_loop_can_finish_without_tool_call(tmp_path):
    loop = AgentLoop(
        llm=FakeLLM(),
        tool_registry=FakeRegistry(),
        settings=make_settings(tmp_path),
        event_bus=EventBus(),
        context_manager=ContextManager(4),
        verifier=FakeVerifier(),
        checkpoint_manager=FakeCheckpointManager(),
    )
    result = loop.run(Session(), "测试任务")
    assert result.success is True
    assert result.message == "任务完成"
    assert result.steps == 1
