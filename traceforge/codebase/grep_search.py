"""在代码库文本文件中执行正则搜索。"""

from __future__ import annotations

import fnmatch
import re

from traceforge.workspace.workspace import Workspace

from .common import TEXT_EXTENSIONS, is_ignored


def grep_search(
    workspace: Workspace,
    pattern: str,
    path: str = ".",
    file_pattern: str = "*",
    max_results: int = 80,
) -> str:
    """搜索匹配文本，并返回 文件:行号:内容。"""
    root = workspace.resolve(path)
    if not root.exists() or not root.is_dir():
        raise NotADirectoryError(f"搜索目录不存在：{path}")

    regex = re.compile(pattern)
    max_results = max(1, min(int(max_results), 300))
    results: list[str] = []

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(workspace.root)
        if is_ignored(relative):
            continue
        if file_path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if not fnmatch.fnmatch(file_path.name, file_pattern):
            continue

        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue

        for line_no, line in enumerate(lines, start=1):
            if regex.search(line):
                snippet = line.strip()
                if len(snippet) > 240:
                    snippet = snippet[:240] + "..."
                results.append(f"{relative}:{line_no}: {snippet}")
                if len(results) >= max_results:
                    return "\n".join(results) + "\n...[结果达到上限]"

    return "\n".join(results) or "(no matches)"
