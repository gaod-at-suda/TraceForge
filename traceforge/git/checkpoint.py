"""安全的 Git Checkpoint。

仅在“已经是 Git 仓库且任务开始前工作区干净”时启用。
这样 rollback 才不会覆盖用户原本未提交的修改。
"""

from __future__ import annotations

import hashlib
import os
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
    """创建、校验和恢复干净 Git 工作区的基线。"""

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

    def worktree_fingerprint(self) -> str | None:
        """生成当前 Git 工作树指纹，用于安全确认“任务结束后未再被修改”。

        指纹覆盖当前 HEAD、所有已跟踪文件相对 HEAD 的差异，以及未跟踪且未被
        .gitignore 排除的文件内容。忽略文件（例如 .env）和 .git 元数据不参与比较。
        """
        if not (self.workspace.root / ".git").exists():
            return None

        head = self._run_bytes(["git", "rev-parse", "HEAD"])
        diff = self._run_bytes(["git", "diff", "--binary", "HEAD", "--"])
        untracked = self._run_bytes(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"]
        )
        if any(result.returncode != 0 for result in (head, diff, untracked)):
            return None

        digest = hashlib.sha256()
        digest.update(b"HEAD\0")
        digest.update(head.stdout)
        digest.update(b"\0DIFF\0")
        digest.update(diff.stdout)
        digest.update(b"\0UNTRACKED\0")
        digest.update(untracked.stdout)

        for raw_path in filter(None, untracked.stdout.split(b"\0")):
            try:
                relative = os.fsdecode(raw_path)
                path = self.workspace.root / relative
                digest.update(b"\0PATH\0")
                digest.update(raw_path)
                digest.update(b"\0CONTENT\0")
                if path.is_symlink():
                    digest.update(os.fsencode(os.readlink(path)))
                else:
                    digest.update(path.read_bytes())
            except OSError:
                # 无法稳定读取工作树时宁可禁用手动恢复，也不执行破坏性回滚。
                return None

        return digest.hexdigest()

    def differs_from(self, checkpoint: GitCheckpoint) -> bool | None:
        """判断当前工作树是否仍包含相对 Checkpoint 的任务改动。"""
        if not checkpoint.enabled or not checkpoint.revision:
            return None

        head = self._run(["git", "rev-parse", "HEAD"])
        status = self._run(["git", "status", "--porcelain", "--untracked-files=all"])
        if head.returncode != 0 or status.returncode != 0:
            return None
        return head.stdout.strip() != checkpoint.revision or bool(status.stdout.strip())

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

    def _run_bytes(self, args: list[str]):
        return subprocess.run(
            args,
            cwd=self.workspace.root,
            capture_output=True,
        )
