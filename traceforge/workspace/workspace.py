"""Workspace 封装。

所有文件工具都通过 Workspace 解析路径，从而统一完成路径规范化
和越界访问检查。
"""

from __future__ import annotations

from pathlib import Path

from .security import ensure_inside_workspace


class Workspace:
    """表示 Agent 当前允许操作的项目目录。"""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.exists():
            raise FileNotFoundError(f"工作区不存在：{self.root}")
        if not self.root.is_dir():
            raise NotADirectoryError(f"工作区不是目录：{self.root}")

    def resolve(self, relative_path: str | Path = ".") -> Path:
        """把相对路径解析为安全的绝对路径。"""
        target = (self.root / Path(relative_path)).resolve()
        ensure_inside_workspace(self.root, target)
        return target
