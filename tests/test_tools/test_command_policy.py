"""Shell 命令安全策略测试。"""

from traceforge.tools.command_tools.policy import CommandPolicy


def test_safe_command_allowed():
    decision = CommandPolicy().evaluate("pytest -q")
    assert decision.allowed is True
    assert decision.level == "safe"


def test_destructive_command_blocked():
    decision = CommandPolicy().evaluate("rm -rf /")
    assert decision.allowed is False
