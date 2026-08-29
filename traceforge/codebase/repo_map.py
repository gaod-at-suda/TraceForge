"""生成精简代码库地图。"""

from __future__ import annotations

from traceforge.workspace.workspace import Workspace

from .common import TEXT_EXTENSIONS, is_ignored
from .symbols import extract_symbols


def repo_map(
    workspace: Workspace,
    path: str = ".",
    max_files: int = 80,
    max_symbols_per_file: int = 12,
) -> str:
    """展示文件和关键符号，减少 LLM 逐文件盲读。"""
    root = workspace.resolve(path)
    if not root.exists() or not root.is_dir():
        raise NotADirectoryError(f"目录不存在：{path}")

    max_files = max(1, min(int(max_files), 200))
    max_symbols_per_file = max(1, min(int(max_symbols_per_file), 30))
    output: list[str] = []
    seen = 0

    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(workspace.root)
        if is_ignored(relative):
            continue
        if file_path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        seen += 1
        output.append(str(relative))
        try:
            text = file_path.read_text(encoding="utf-8")
            symbols = extract_symbols(file_path, text)
        except (UnicodeDecodeError, OSError):
            symbols = []

        for symbol in symbols[:max_symbols_per_file]:
            output.append(
                f"  L{symbol.line:<4} {symbol.kind:<8} {symbol.name}"
            )
        if len(symbols) > max_symbols_per_file:
            output.append(
                f"  ... 还有 {len(symbols) - max_symbols_per_file} 个符号"
            )

        if seen >= max_files:
            output.append("...[文件数量达到 Repo Map 上限]")
            break

    return "\n".join(output) or "(empty repository map)"
