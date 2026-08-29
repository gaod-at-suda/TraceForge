"""按 glob 模式搜索项目文件。"""

from __future__ import annotations

from traceforge.workspace.workspace import Workspace

from .common import is_ignored


def glob_files(
    workspace: Workspace,
    pattern: str,
    path: str = ".",
    max_results: int = 100,
) -> str:
    """返回匹配 glob 的相对路径，结果数量受限。"""
    root = workspace.resolve(path)
    if not root.exists() or not root.is_dir():
        raise NotADirectoryError(f"搜索目录不存在：{path}")

    max_results = max(1, min(int(max_results), 300))
    matches: list[str] = []

    for target in root.glob(pattern):
        relative = target.relative_to(workspace.root)
        if is_ignored(relative):
            continue
        suffix = "/" if target.is_dir() else ""
        matches.append(f"{relative}{suffix}")
        if len(matches) >= max_results:
            break

    return "\n".join(sorted(matches)) or "(no matches)"
