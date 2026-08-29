"""ToolRegistry Never-Throw 边界测试。"""

from traceforge.config.settings import Settings
from traceforge.tools.registry import ToolRegistry
from traceforge.workspace.workspace import Workspace


def make_settings(tmp_path):
    return Settings(
        api_key="x",
        model_name="fake",
        base_url=None,
        max_steps=3,
        command_timeout=1,
        max_tool_output=1000,
        max_history_turns=3,
        max_context_chars=48000,
        condensed_summary_chars=6000,
        verification_retries=2,
        runtime_dir=tmp_path / "runtime",
        agent_mode="auto",
    )


def test_unknown_tool_returns_failure(tmp_path):
    registry = ToolRegistry(Workspace(tmp_path), make_settings(tmp_path))
    result = registry.execute("missing_tool", {})
    assert result.success is False
    assert "未知工具" in result.error
