"""工作区安全检查。

当前重点防止路径穿越，让 Agent 只能操作用户明确指定的 workspace。
"""

from __future__ import annotations

from pathlib import Path

from traceforge.exceptions import WorkspaceSecurityError


def ensure_inside_workspace(root: Path, target: Path) -> None:
    """确认 target 位于 root 内部，否则拒绝访问。"""
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise WorkspaceSecurityError(
            f"禁止访问工作区之外的路径：{target}"
        ) from exc
