"""Workspace 越界访问测试。"""

from pathlib import Path

import pytest

from traceforge.exceptions import WorkspaceSecurityError
from traceforge.workspace.workspace import Workspace


def test_workspace_allows_inner_path(tmp_path: Path):
    """工作区内部路径应正常解析。"""
    workspace = Workspace(tmp_path)
    target = workspace.resolve("src/main.py")
    assert target == (tmp_path / "src/main.py").resolve()


def test_workspace_blocks_parent_escape(tmp_path: Path):
    """通过 .. 尝试逃逸工作区时必须被拒绝。"""
    workspace = Workspace(tmp_path)

    with pytest.raises(WorkspaceSecurityError):
        workspace.resolve("../secret.txt")
