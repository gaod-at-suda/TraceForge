"""安全的 Git Checkpoint。

仅在“已经是 Git 仓库且任务开始前工作区干净”时启用。
这样 rollback 才不会覆盖用户原本未提交的修改。
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from traceforge.workspace.workspace import Workspace


@dataclass(frozen=True)
class GitCheckpoint:
    """一次可回滚的 Git 基线。"""

    enabled: bool
    revision: str = ""
    reason: str = ""


class GitCheckpointManager:
    """创建和恢复干净 Git 工作区的基线。"""

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def create(self) -> GitCheckpoint:
        """读取当前 HEAD；若仓库不干净则安全禁用回滚。"""
        if not (self.workspace.root / ".git").exists():
            return GitCheckpoint(False, reason="当前 workspace 不是 Git 仓库")

        status = self._run(["git", "status", "--porcelain"])
        if status.returncode != 0:
            return GitCheckpoint(False, reason="无法读取 Git 状态")
        if status.stdout.strip():
            return GitCheckpoint(
                False,
                reason="任务开始前存在未提交修改，为避免覆盖用户工作，禁用自动回滚",
            )

        head = self._run(["git", "rev-parse", "HEAD"])
        if head.returncode != 0:
            return GitCheckpoint(False, reason="Git 仓库还没有可用 HEAD")

        return GitCheckpoint(True, head.stdout.strip(), "已记录干净 Git 基线")

    def rollback(self, checkpoint: GitCheckpoint) -> bool:
        """恢复到基线并清理本次任务产生的未跟踪文件。"""
        if not checkpoint.enabled or not checkpoint.revision:
            return False

        reset = self._run(["git", "reset", "--hard", checkpoint.revision])
        clean = self._run(["git", "clean", "-fd"])
        return reset.returncode == 0 and clean.returncode == 0

    def _run(self, args: list[str]):
        return subprocess.run(
            args,
            cwd=self.workspace.root,
            capture_output=True,
            text=True,
        )
