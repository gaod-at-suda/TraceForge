"""Git Checkpoint 测试。"""

from pathlib import Path
import subprocess

from traceforge.git import GitCheckpointManager
from traceforge.workspace.workspace import Workspace


def _run(cwd: Path, *args: str):
    subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def test_clean_repo_can_rollback(tmp_path: Path):
    _run(tmp_path, "git", "init", "-q")
    (tmp_path / "a.txt").write_text("base\n", encoding="utf-8")
    _run(tmp_path, "git", "add", ".")
    _run(
        tmp_path,
        "git",
        "-c", "user.name=Test",
        "-c", "user.email=test@example.invalid",
        "commit", "-q", "-m", "base",
    )

    manager = GitCheckpointManager(Workspace(tmp_path))
    checkpoint = manager.create()
    assert checkpoint.enabled is True

    (tmp_path / "a.txt").write_text("changed\n", encoding="utf-8")
    (tmp_path / "new.txt").write_text("new\n", encoding="utf-8")

    assert manager.rollback(checkpoint) is True
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "base\n"
    assert not (tmp_path / "new.txt").exists()


def test_worktree_fingerprint_tracks_task_changes(tmp_path: Path):
    _run(tmp_path, "git", "init", "-q")
    (tmp_path / "a.txt").write_text("base\n", encoding="utf-8")
    _run(tmp_path, "git", "add", ".")
    _run(
        tmp_path,
        "git",
        "-c", "user.name=Test",
        "-c", "user.email=test@example.invalid",
        "commit", "-q", "-m", "base",
    )

    manager = GitCheckpointManager(Workspace(tmp_path))
    clean = manager.worktree_fingerprint()
    assert clean is not None

    (tmp_path / "a.txt").write_text("changed\n", encoding="utf-8")
    tracked_changed = manager.worktree_fingerprint()
    assert tracked_changed is not None
    assert tracked_changed != clean

    (tmp_path / "new.txt").write_text("first\n", encoding="utf-8")
    untracked_first = manager.worktree_fingerprint()
    (tmp_path / "new.txt").write_text("second\n", encoding="utf-8")
    untracked_second = manager.worktree_fingerprint()
    assert untracked_first is not None
    assert untracked_second is not None
    assert untracked_first != untracked_second
