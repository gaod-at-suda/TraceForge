"""Tool 权限策略。

PLAN 模式只允许只读工具；
AUTO 模式允许正常执行；
CONFIRM 模式保留工具可见性，但会拦截写操作，便于未来接 Web 审批按钮。
"""

from __future__ import annotations

from dataclasses import dataclass

from .mode import AgentMode


@dataclass(frozen=True)
class PermissionDecision:
    """描述某次工具调用是否被宿主策略允许。"""

    allowed: bool
    reason: str


class ToolPermissionPolicy:
    """把模型决策与宿主执行权限分离。"""

    READ_ONLY = {
        "list_directory",
        "read_file",
        "glob_files",
        "grep_search",
        "repo_map",
    }
    MUTATING = {"write_file", "replace_in_file", "apply_patch"}
    EXECUTION = {"run_command"}

    def __init__(self, mode: AgentMode) -> None:
        self.mode = mode

    def visible(self, tool_name: str) -> bool:
        """PLAN 模式直接隐藏有副作用工具。"""
        if self.mode == AgentMode.PLAN:
            return tool_name in self.READ_ONLY
        return True

    def check(self, tool_name: str) -> PermissionDecision:
        """真正执行前再做一次权限校验。"""
        if self.mode == AgentMode.AUTO:
            return PermissionDecision(True, "AUTO 模式允许执行")

        if tool_name in self.READ_ONLY:
            return PermissionDecision(True, "只读工具允许执行")

        if self.mode == AgentMode.PLAN:
            return PermissionDecision(False, "PLAN 模式禁止写文件和执行命令")

        return PermissionDecision(
            False,
            "CONFIRM 模式下该操作需要用户审批；当前自动测试不会自动批准",
        )
