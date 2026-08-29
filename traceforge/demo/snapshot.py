"""测试工作区快照与 Diff。

在 Agent 执行前后分别读取文本文件，用于生成最终修改摘要。
"""

from __future__ import annotations

import difflib
from pathlib import Path


IGNORED_DIRS = {"__pycache__", ".pytest_cache", ".git", ".idea"}


def snapshot_text_files(root: Path) -> dict[str, str]:
    """读取工作区中常见文本文件，形成相对路径 -> 内容的快照。"""
    snapshot: dict[str, str] = {}

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        snapshot[str(path.relative_to(root))] = content

    return snapshot


def compare_snapshots(
    before: dict[str, str],
    after: dict[str, str],
) -> dict[str, str]:
    """比较两个快照，返回所有发生变化文件的 unified diff。"""
    diffs: dict[str, str] = {}
    all_paths = sorted(set(before) | set(after))

    for relative_path in all_paths:
        old = before.get(relative_path, "")
        new = after.get(relative_path, "")
        if old == new:
            continue

        diff = difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
            lineterm="",
        )
        diffs[relative_path] = "\n".join(diff)

    return diffs
