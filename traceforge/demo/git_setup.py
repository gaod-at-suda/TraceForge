"""为可重复 Demo 创建本地 Git 基线。

只作用于每次自动重建的 demo_project，不会碰用户真实仓库。
"""

from __future__ import annotations

import subprocess
from pathlib import Path


_DEMO_GITIGNORE_ENTRIES = (
    "__pycache__/",
    ".pytest_cache/",
    "*.py[cod]",
)


def _ensure_demo_gitignore(workspace: Path) -> None:
    """确保 Demo 的 Python 测试缓存不会把 Git 工作区弄脏。

    baseline pytest 会生成 ``__pycache__`` / ``.pytest_cache``。如果这些
    文件没有被忽略，Agent 启动时会误判为“任务开始前已有未提交修改”，
    从而安全地禁用 Git Checkpoint。这里只修改一次性 demo_project。
    """
    gitignore = workspace / ".gitignore"

    if gitignore.exists():
        original = gitignore.read_text(encoding="utf-8")
        lines = original.splitlines()
    else:
        original = ""
        lines = []

    existing = {line.strip() for line in lines}
    missing = [entry for entry in _DEMO_GITIGNORE_ENTRIES if entry not in existing]
    if not missing:
        return

    text = original
    if text and not text.endswith("\n"):
        text += "\n"
    text += "\n".join(missing) + "\n"
    gitignore.write_text(text, encoding="utf-8")


def initialize_demo_git(workspace: Path) -> None:
    """初始化仓库并提交干净基线，便于测试 Checkpoint 能力。"""
    _ensure_demo_gitignore(workspace)

    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
    subprocess.run(["git", "add", "."], cwd=workspace, check=True)
    subprocess.run(
        [
            "git",
            "-c", "user.name=TraceForge",
            "-c", "user.email=traceforge@example.invalid",
            "commit",
            "-q",
            "-m", "demo baseline",
        ],
        cwd=workspace,
        check=True,
    )
