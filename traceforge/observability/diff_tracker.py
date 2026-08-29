"""文件变更 Diff 生成。"""

from __future__ import annotations

import difflib
from traceforge.workspace.workspace import Workspace


class DiffTracker:
    """在写文件前后生成 unified diff，供 Trace 和 Web Console 展示。"""

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def snapshot(self, path: str) -> str | None:
        target = self.workspace.resolve(path)
        if not target.exists() or not target.is_file():
            return None
        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None

    def make_diff(self, path: str, before: str | None) -> str:
        target = self.workspace.resolve(path)
        try:
            after = target.read_text(encoding="utf-8") if target.exists() else ""
        except UnicodeDecodeError:
            return "(二进制或非 UTF-8 文件，无法展示文本 Diff)"

        old = before or ""
        diff = difflib.unified_diff(
            old.splitlines(),
            after.splitlines(),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
        )
        return "\n".join(diff) or "(文件内容无变化)"
