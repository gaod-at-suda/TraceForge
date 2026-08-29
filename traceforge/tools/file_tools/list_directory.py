"""目录浏览工具。"""

from __future__ import annotations

from traceforge.workspace.workspace import Workspace


def list_directory(workspace: Workspace, path: str = ".") -> str:
    """列出指定目录的直接子项，并标记文件/目录类型。"""
    target = workspace.resolve(path)

    if not target.exists():
        raise FileNotFoundError(f"目录不存在：{path}")
    if not target.is_dir():
        raise NotADirectoryError(f"目标不是目录：{path}")

    items = []
    for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        kind = "DIR " if child.is_dir() else "FILE"
        relative = child.relative_to(workspace.root)
        items.append(f"[{kind}] {relative}")

    return "\n".join(items) if items else "(empty directory)"
