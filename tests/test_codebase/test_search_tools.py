"""代码库 grep/glob 工具测试。"""

from pathlib import Path

from traceforge.codebase import glob_files, grep_search
from traceforge.workspace.workspace import Workspace


def test_glob_and_grep(tmp_path: Path):
    """glob 与 grep 的路径断言应兼容 Windows / Linux / macOS。"""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text(
        "class UserService:\n    pass\n",
        encoding="utf-8",
    )
    workspace = Workspace(tmp_path)

    # 不把路径分隔符写死为 '/'：
    # Windows 下 Path 会生成 src\\service.py，Linux/macOS 下生成 src/service.py。
    expected_path = str(Path("src") / "service.py")

    glob_result = glob_files(workspace, "**/*.py")
    assert expected_path in glob_result

    grep_result = grep_search(
        workspace,
        "UserService",
        file_pattern="*.py",
    )
    assert f"{expected_path}:1:" in grep_result
