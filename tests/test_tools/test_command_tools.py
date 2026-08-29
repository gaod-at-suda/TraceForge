"""命令工具基础测试。"""

from pathlib import Path
import sys

from traceforge.tools.command_tools import run_command
from traceforge.workspace.workspace import Workspace


def test_run_python_command(tmp_path: Path):
    """验证命令能够在 workspace 内正常执行。"""
    workspace = Workspace(tmp_path)

    command = f'"{sys.executable}" -c "print(123)"'
    result = run_command(workspace, command, timeout=10)

    assert "exit_code: 0" in result
    assert "123" in result
