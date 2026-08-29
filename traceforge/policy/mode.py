"""Agent 运行模式。"""

from __future__ import annotations

from enum import Enum


class AgentMode(str, Enum):
    """控制 Agent 能否执行有副作用的工具。"""

    PLAN = "plan"
    AUTO = "auto"
    CONFIRM = "confirm"

    @classmethod
    def parse(cls, value: str) -> "AgentMode":
        """把环境变量字符串安全转换为枚举。"""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.AUTO
