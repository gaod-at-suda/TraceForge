"""文件写入工具。"""

from __future__ import annotations

from traceforge.workspace.workspace import Workspace


def write_file(workspace: Workspace, path: str, content: str) -> str:
    """创建或完整覆盖文本文件；若父目录不存在则自动创建。"""
    target = workspace.resolve(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    relative = target.relative_to(workspace.root)
    return f"已写入文件：{relative}"
