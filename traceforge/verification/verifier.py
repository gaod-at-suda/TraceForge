"""宿主侧自动验证器。

验证由 runtime 主动执行，而不是仅依赖 Prompt 要求模型自觉测试。
"""

from __future__ import annotations

import subprocess

from traceforge.workspace.workspace import Workspace

from .detector import detect_verification
from .result import VerificationResult


class Verifier:
    """检测并执行项目验证命令。"""

    def __init__(self, workspace: Workspace, timeout: int = 60) -> None:
        self.workspace = workspace
        self.timeout = max(5, int(timeout))

    def verify(self) -> VerificationResult:
        """执行检测到的验证计划。"""
        plan = detect_verification(self.workspace)
        if not plan.detected:
            return VerificationResult(
                detected=False,
                success=True,
                command="",
                reason=plan.reason,
                return_code=None,
                output="未检测到自动验证入口，跳过宿主侧验证。",
            )

        try:
            completed = subprocess.run(
                plan.command,
                cwd=self.workspace.root,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return VerificationResult(
                True,
                False,
                " ".join(plan.command),
                plan.reason,
                None,
                f"自动验证超过 {self.timeout} 秒，已终止。",
            )
        except OSError as exc:
            return VerificationResult(
                True,
                False,
                " ".join(plan.command),
                plan.reason,
                None,
                f"无法启动验证命令：{exc}",
            )

        output = "\n".join(
            part.strip()
            for part in (completed.stdout, completed.stderr)
            if part and part.strip()
        ) or "(no output)"

        return VerificationResult(
            detected=True,
            success=completed.returncode == 0,
            command=" ".join(plan.command),
            reason=plan.reason,
            return_code=completed.returncode,
            output=output,
        )
