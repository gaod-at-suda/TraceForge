"""文件 Diff 记录测试。"""

from traceforge.observability.diff_tracker import DiffTracker
from traceforge.workspace.workspace import Workspace


def test_diff_tracker_reports_change(tmp_path):
    path = tmp_path / "a.py"
    path.write_text("x = 1\n", encoding="utf-8")
    tracker = DiffTracker(Workspace(tmp_path))
    before = tracker.snapshot("a.py")
    path.write_text("x = 2\n", encoding="utf-8")
    diff = tracker.make_diff("a.py", before)
    assert "-x = 1" in diff
    assert "+x = 2" in diff
