"""Plan/Auto/Confirm 权限策略测试。"""

from traceforge.policy import AgentMode, ToolPermissionPolicy


def test_plan_mode_only_allows_read_only_tools():
    policy = ToolPermissionPolicy(AgentMode.PLAN)

    assert policy.check("repo_map").allowed is True
    assert policy.check("read_file").allowed is True
    assert policy.check("apply_patch").allowed is False
    assert policy.check("run_command").allowed is False


def test_auto_mode_allows_mutation():
    policy = ToolPermissionPolicy(AgentMode.AUTO)
    assert policy.check("apply_patch").allowed is True
