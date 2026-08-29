"""结构化 Patch 测试。"""

from pathlib import Path

import pytest

from traceforge.edit import apply_patch
from traceforge.workspace.workspace import Workspace


def test_apply_patch_replaces_lines(tmp_path: Path):
    target = tmp_path / "a.py"
    target.write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    apply_patch(
        workspace,
        "a.py",
        start_line=2,
        end_line=2,
        replacement="b = 20\n",
        expected_text="b = 2\n",
    )

    assert target.read_text(encoding="utf-8") == "a = 1\nb = 20\nc = 3\n"


def test_apply_patch_detects_stale_content(tmp_path: Path):
    target = tmp_path / "a.py"
    target.write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(ValueError):
        apply_patch(
            Workspace(tmp_path),
            "a.py",
            1,
            1,
            "x = 2\n",
            expected_text="x = 999\n",
        )
