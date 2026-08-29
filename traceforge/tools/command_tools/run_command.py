"""受 workspace、策略检查和 timeout 保护的本地命令执行。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from traceforge.exceptions import CommandTimeoutError
from traceforge.workspace.workspace import Workspace

from .policy import CommandPolicy


def _build_command_env() -> dict[str, str]:
    """让子进程优先使用启动 TraceForge 的 Python 环境。

    TraceForge 可能通过 ``venv/Scripts/python.exe`` 启动，但 Windows 的
    ``shell=True`` 子命令仍会按照系统 PATH 解析裸 ``python`` / ``pytest``。
    因此把当前解释器目录放到 PATH 最前面，保证 Agent 执行命令时优先
    使用与 TraceForge 自身一致的虚拟环境。
    """
    env = os.environ.copy()

    interpreter_dir = str(Path(sys.executable).resolve().parent)
    current_path = env.get("PATH", "")
    env["PATH"] = (
        interpreter_dir
        if not current_path
        else interpreter_dir + os.pathsep + current_path
    )

    # 如果当前进程运行在 venv 中，也把 VIRTUAL_ENV 传给子进程。
    if sys.prefix != sys.base_prefix:
        env["VIRTUAL_ENV"] = sys.prefix

    return env


def run_command(
    workspace: Workspace,
    command: str,
    timeout: int,
    policy: CommandPolicy | None = None,
) -> str:
    """执行命令并返回 policy、exit code、stdout 和 stderr。"""
    policy = policy or CommandPolicy()
    decision = policy.evaluate(command)
    if not decision.allowed:
        raise PermissionError(f"命令被安全策略拦截：{decision.reason}")

    try:
        completed = subprocess.run(
            command,
            cwd=workspace.root,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_build_command_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise CommandTimeoutError(
            f"命令执行超过 {timeout} 秒，已终止：{command}"
        ) from exc

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    return (
        f"policy: {decision.level} ({decision.reason})\n"
        f"exit_code: {completed.returncode}\n"
        f"stdout:\n{stdout or '(empty)'}\n"
        f"stderr:\n{stderr or '(empty)'}"
    )
