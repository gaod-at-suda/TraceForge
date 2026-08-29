"""Agent Loop 宿主自动验证失败后重新反馈给 LLM 的测试。"""

from dataclasses import dataclass

from traceforge.agent.context import ContextManager
from traceforge.agent.loop import AgentLoop
from traceforge.config.settings import Settings
from traceforge.events import EventBus
from traceforge.git import GitCheckpoint
from traceforge.llm.messages import LLMResponse
from traceforge.session import Session
from traceforge.verification import VerificationResult


class FakeLLM:
    """连续两次尝试结束任务，用于验证失败后的 retry。"""

    def __init__(self):
        self.calls = 0

    def chat(self, messages, tools):
        self.calls += 1
        return LLMResponse(content=f"完成尝试 {self.calls}", tool_calls=[])


class MutatedRegistry:
    """模拟本轮已经发生过文件修改。"""

    schemas = []

    def __init__(self):
        self.mutation_count = 1

    def reset_run_state(self):
        self.mutation_count = 1


class SequenceVerifier:
    def __init__(self):
        self.calls = 0

    def verify(self):
        self.calls += 1
        if self.calls == 1:
            return VerificationResult(
                True, False, "pytest -q", "test", 1, "1 failed"
            )
        return VerificationResult(
            True, True, "pytest -q", "test", 0, "3 passed"
        )


class FakeCheckpointManager:
    def create(self):
        return GitCheckpoint(False, reason="test")


def test_failed_verification_is_fed_back_and_retried(tmp_path):
    settings = Settings(
        api_key="x",
        model_name="fake",
        base_url=None,
        max_steps=4,
        command_timeout=5,
        max_tool_output=1000,
        max_history_turns=8,
        max_context_chars=48000,
        condensed_summary_chars=6000,
        verification_retries=2,
        runtime_dir=tmp_path / "runtime",
        agent_mode="auto",
    )
    llm = FakeLLM()
    verifier = SequenceVerifier()
    session = Session()

    loop = AgentLoop(
        llm=llm,
        tool_registry=MutatedRegistry(),
        settings=settings,
        event_bus=EventBus(),
        context_manager=ContextManager(8),
        verifier=verifier,
        checkpoint_manager=FakeCheckpointManager(),
    )
    result = loop.run(session, "修改代码")

    assert result.success is True
    assert llm.calls == 2
    assert verifier.calls == 2
    assert any(
        message.get("role") == "user"
        and "HOST AUTOMATIC VERIFICATION FAILED" in message.get("content", "")
        for message in session.messages
    )
