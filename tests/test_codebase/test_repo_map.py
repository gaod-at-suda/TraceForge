"""Repo Map 测试。"""

from pathlib import Path

from traceforge.codebase import repo_map
from traceforge.workspace.workspace import Workspace


def test_repo_map_extracts_python_symbols(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "class App:\n"
        "    def run(self):\n"
        "        pass\n\n"
        "def helper():\n"
        "    pass\n",
        encoding="utf-8",
    )
    output = repo_map(Workspace(tmp_path))

    assert "app.py" in output
    assert "class    App" in output
    assert "method   App.run" in output
    assert "function helper" in output
