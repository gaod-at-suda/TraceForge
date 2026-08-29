"""结构化行区间 Patch。

相比整文件覆盖，Patch 只修改明确行区间；可选 expected_text
用于乐观并发校验，避免文件已变化时误改。
"""

from __future__ import annotations

from traceforge.workspace.workspace import Workspace


def apply_patch(
    workspace: Workspace,
    path: str,
    start_line: int,
    end_line: int,
    replacement: str,
    expected_text: str | None = None,
) -> str:
    """替换 [start_line, end_line]；也支持 start_line=end_line+1 的插入。"""
    target = workspace.resolve(path)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"文件不存在：{path}")

    original = target.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    total = len(lines)

    start_line = int(start_line)
    end_line = int(end_line)
    if start_line < 1 or start_line > total + 1:
        raise ValueError(f"start_line 越界：1..{total + 1}")
    if end_line < 0 or end_line > total:
        raise ValueError(f"end_line 越界：0..{total}")
    if end_line < start_line - 1:
        raise ValueError("end_line 只能等于/大于 start_line-1")

    start_idx = start_line - 1
    end_idx = end_line
    current = "".join(lines[start_idx:end_idx])

    if expected_text is not None and current != expected_text:
        raise ValueError(
            "Patch 校验失败：目标行内容与 expected_text 不一致，"
            "请重新 read_file 获取最新内容后再修改。"
        )

    replacement_lines = replacement.splitlines(keepends=True)
    if replacement and not replacement_lines:
        replacement_lines = [replacement]

    updated = lines[:start_idx] + replacement_lines + lines[end_idx:]
    target.write_text("".join(updated), encoding="utf-8")

    action = "插入" if end_line == start_line - 1 else "替换"
    return (
        f"已{action} {path} 的行区间 "
        f"{start_line}-{end_line if end_line >= start_line else start_line - 1}"
    )
