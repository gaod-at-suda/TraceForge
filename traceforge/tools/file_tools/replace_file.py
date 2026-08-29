"""局部文本替换工具。"""

from __future__ import annotations

from traceforge.workspace.workspace import Workspace


def replace_in_file(
    workspace: Workspace,
    path: str,
    old_text: str,
    new_text: str,
) -> str:
    """仅当 old_text 在文件中唯一出现时执行替换，避免误改多处代码。"""
    target = workspace.resolve(path)

    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"文件不存在：{path}")

    content = target.read_text(encoding="utf-8")
    count = content.count(old_text)

    if count == 0:
        raise ValueError("old_text 在文件中不存在，无法替换。")
    if count > 1:
        raise ValueError(
            f"old_text 在文件中出现 {count} 次，请提供更精确的上下文。"
        )

    updated = content.replace(old_text, new_text, 1)
    target.write_text(updated, encoding="utf-8")
    return f"已完成局部替换：{path}"
