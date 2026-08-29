"""运行配置读取。

API Key 等敏感信息只从环境变量读取，不写死在源码中。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .constants import (
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_CONDENSED_SUMMARY_CHARS,
    DEFAULT_MAX_CONTEXT_CHARS,
    DEFAULT_MAX_HISTORY_TURNS,
    DEFAULT_MAX_STEPS,
    DEFAULT_MAX_TOOL_OUTPUT,
    DEFAULT_VERIFICATION_RETRIES,
)


@dataclass(frozen=True)
class Settings:
    """TraceForge 的运行配置。"""

    api_key: str
    model_name: str
    base_url: str | None
    max_steps: int
    command_timeout: int
    max_tool_output: int
    max_history_turns: int
    max_context_chars: int
    condensed_summary_chars: int
    verification_retries: int
    runtime_dir: Path
    agent_mode: str

    @classmethod
    def from_env(cls, require_api_key: bool = True) -> "Settings":
        """从环境变量构建配置对象。"""
        api_key = os.getenv("TRACEFORGE_API_KEY", "").strip()
        if require_api_key and not api_key:
            raise RuntimeError(
                "未检测到 TRACEFORGE_API_KEY，请先在环境变量中配置模型 API Key。"
            )

        return cls(
            api_key=api_key,
            model_name=os.getenv("TRACEFORGE_MODEL", "gpt-4.1-mini").strip(),
            base_url=os.getenv("TRACEFORGE_BASE_URL", "").strip() or None,
            max_steps=int(os.getenv("TRACEFORGE_MAX_STEPS", DEFAULT_MAX_STEPS)),
            command_timeout=int(
                os.getenv("TRACEFORGE_COMMAND_TIMEOUT", DEFAULT_COMMAND_TIMEOUT)
            ),
            max_tool_output=int(
                os.getenv("TRACEFORGE_MAX_TOOL_OUTPUT", DEFAULT_MAX_TOOL_OUTPUT)
            ),
            max_history_turns=int(
                os.getenv("TRACEFORGE_MAX_HISTORY_TURNS", DEFAULT_MAX_HISTORY_TURNS)
            ),
            max_context_chars=int(
                os.getenv("TRACEFORGE_MAX_CONTEXT_CHARS", DEFAULT_MAX_CONTEXT_CHARS)
            ),
            condensed_summary_chars=int(
                os.getenv(
                    "TRACEFORGE_CONDENSED_SUMMARY_CHARS",
                    DEFAULT_CONDENSED_SUMMARY_CHARS,
                )
            ),
            verification_retries=int(
                os.getenv(
                    "TRACEFORGE_VERIFICATION_RETRIES",
                    DEFAULT_VERIFICATION_RETRIES,
                )
            ),
            runtime_dir=Path(
                os.getenv("TRACEFORGE_RUNTIME_DIR", ".traceforge_runtime")
            ).expanduser().resolve(),
            agent_mode=os.getenv("TRACEFORGE_AGENT_MODE", "auto").strip().lower(),
        )
