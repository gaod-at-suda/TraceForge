"""文件工具基础测试。"""

from pathlib import Path

from traceforge.tools.file_tools import (
    list_directory,
    read_file,
    replace_in_file,
    write_file,
)
from traceforge.workspace.workspace import Workspace


def test_file_tool_flow(tmp_path: Path):
    """验证写入、读取、替换和目录浏览的完整流程。"""
    workspace = Workspace(tmp_path)

    write_file(workspace, "src/demo.py", "value = 1\n")
    assert "1 | value = 1" in read_file(workspace, "src/demo.py")

    replace_in_file(
        workspace,
        "src/demo.py",
        "value = 1",
        "value = 2",
    )
    assert "value = 2" in read_file(workspace, "src/demo.py")

    listing = list_directory(workspace, ".")
    assert "src" in listing
