"""自动验证结果。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationResult:
    """保存宿主程序独立验证的真实结果。"""

    detected: bool
    success: bool
    command: str
    reason: str
    return_code: int | None
    output: str
