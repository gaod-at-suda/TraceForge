"""Shell 命令安全策略。

该策略不是完整沙箱，而是在真正执行命令前增加宿主侧最小安全边界。
明确的破坏性系统命令会直接拦截，其它命令仍受 workspace 和 timeout 约束。
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    level: str
    reason: str


class CommandPolicy:
    """基于保守正则规则识别明显危险命令。"""

    _BLOCKED_PATTERNS = [
        (r"(^|[;&|]\s*)rm\s+-rf\s+/(\s|$)", "禁止递归删除系统根目录"),
        (r"(^|[;&|]\s*)shutdown\b", "禁止关闭操作系统"),
        (r"(^|[;&|]\s*)reboot\b", "禁止重启操作系统"),
        (r"(^|[;&|]\s*)format(\.com)?\b", "禁止格式化磁盘"),
        (r"\bdel\s+/[sq]\b.*(?:c:\\\\|[a-z]:\\\\)", "禁止递归删除磁盘内容"),
        (r"\brd\s+/s\b.*(?:c:\\\\|[a-z]:\\\\)", "禁止递归删除磁盘目录"),
        (r"\bmkfs(?:\.|\s)", "禁止创建文件系统"),
        (r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;\s*:", "禁止 fork bomb"),
    ]

    _RISKY_KEYWORDS = (
        "pip install",
        "npm install",
        "git reset",
        "git checkout",
        "git clean",
    )

    def evaluate(self, command: str) -> PolicyDecision:
        normalized = command.strip().lower()
        if not normalized:
            return PolicyDecision(False, "blocked", "命令不能为空")

        for pattern, reason in self._BLOCKED_PATTERNS:
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                return PolicyDecision(False, "blocked", reason)

        if any(keyword in normalized for keyword in self._RISKY_KEYWORDS):
            return PolicyDecision(True, "risky", "命令可能修改依赖或版本控制状态")

        return PolicyDecision(True, "safe", "未命中明显危险规则")
