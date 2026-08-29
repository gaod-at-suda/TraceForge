"""支持分页和行号的文件读取工具。"""

from __future__ import annotations

from traceforge.config.constants import DEFAULT_READ_LINE_COUNT, MAX_READ_LINE_COUNT
from traceforge.workspace.workspace import Workspace


def read_file(
    workspace: Workspace,
    path: str,
    start_line: int = 1,
    line_count: int = DEFAULT_READ_LINE_COUNT,
) -> str:
    """按行读取 UTF-8 文本文件，并显示总行数和行号。

    start_line 从 1 开始；line_count 会被限制到合理范围，避免一次读取巨大文件。
    """
    target = workspace.resolve(path)
    if not target.exists():
        raise FileNotFoundError(f"文件不存在：{path}")
    if not target.is_file():
        raise IsADirectoryError(f"目标不是文件：{path}")
    if start_line < 1:
        raise ValueError("start_line 必须 >= 1")

    line_count = max(1, min(int(line_count), MAX_READ_LINE_COUNT))
    lines = target.read_text(encoding="utf-8").splitlines()
    total = len(lines)

    if total == 0:
        return f"[{path} | empty file]"
    if start_line > total:
        return f"[{path} | 共 {total} 行] start_line={start_line} 已超过文件末尾。"

    end_line = min(total, start_line + line_count - 1)
    selected = lines[start_line - 1 : end_line]
    width = len(str(end_line))
    numbered = [
        f"{line_no:>{width}} | {text}"
        for line_no, text in enumerate(selected, start=start_line)
    ]
    has_more = end_line < total
    footer = (
        f"\n[还有内容：下一次可从 start_line={end_line + 1} 继续读取]"
        if has_more else "\n[已到文件末尾]"
    )
    header = f"[{path} | lines {start_line}-{end_line} / {total}]"
    return header + "\n" + "\n".join(numbered) + footer
