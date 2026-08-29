"""自动验证测试。"""

from pathlib import Path

from traceforge.verification import Verifier
from traceforge.workspace.workspace import Workspace


def test_python_project_is_verified(tmp_path: Path):
    (tmp_path / "test_ok.py").write_text(
        "def test_ok():\n    assert 1 + 1 == 2\n",
        encoding="utf-8",
    )

    result = Verifier(Workspace(tmp_path), timeout=20).verify()

    assert result.detected is True
    assert result.success is True
    assert "pytest" in result.command
