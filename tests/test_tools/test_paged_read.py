"""分页文件读取测试。"""

from traceforge.tools.file_tools.read_file import read_file
from traceforge.workspace.workspace import Workspace


def test_read_file_supports_line_range(tmp_path):
    (tmp_path / "demo.txt").write_text("\n".join(f"line{i}" for i in range(1, 11)), encoding="utf-8")
    result = read_file(Workspace(tmp_path), "demo.txt", start_line=4, line_count=3)
    assert "lines 4-6 / 10" in result
    assert "4 | line4" in result
    assert "start_line=7" in result
