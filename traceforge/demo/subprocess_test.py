"""独立 pytest 执行辅助函数。

验证测试结果时使用独立子进程，确保最终 PASS 不是由 LLM 自己声称的，
而是宿主程序真正执行 pytest 得到的。
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PytestResult:
    """保存一次 pytest 子进程的真实执行结果。"""

    success: bool
    return_code: int
    output: str


def run_pytest(target_dir: Path, extra_args: list[str] | None = None) -> PytestResult:
    """在 target_dir 中执行 pytest，并捕获完整输出。"""
    args = [sys.executable, "-m", "pytest", "-q"]
    if extra_args:
        args.extend(extra_args)

    completed = subprocess.run(
        args,
        cwd=target_dir,
        capture_output=True,
        text=True,
    )

    output_parts = []
    if completed.stdout.strip():
        output_parts.append(completed.stdout.strip())
    if completed.stderr.strip():
        output_parts.append(completed.stderr.strip())

    return PytestResult(
        success=completed.returncode == 0,
        return_code=completed.returncode,
        output="\n".join(output_parts) or "(pytest 无输出)",
    )
