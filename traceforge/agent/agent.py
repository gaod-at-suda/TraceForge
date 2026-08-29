"""CodingAgent 对外入口。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from traceforge.config.settings import Settings
from traceforge.events.bus import EventBus
from traceforge.git import GitCheckpointManager
from traceforge.session.session import Session
from traceforge.tools.registry import ToolRegistry
from traceforge.verification import Verifier

from .context import ContextManager
from .loop import AgentLoop
from .result import AgentResult

if TYPE_CHECKING:
    from traceforge.llm.client import LLMClient
else:
    LLMClient = Any


class CodingAgent:
    """持有长期 Session，并把具体执行交给 AgentLoop。"""

    def __init__(
        self,
        llm: LLMClient,
        tool_registry: ToolRegistry,
        settings: Settings,
        event_bus: EventBus,
        session: Session,
        verifier: Verifier,
        checkpoint_manager: GitCheckpointManager,
    ) -> None:
        self.session = session
        self.loop = AgentLoop(
            llm=llm,
            tool_registry=tool_registry,
            settings=settings,
            event_bus=event_bus,
            context_manager=ContextManager(
                settings.max_history_turns,
                settings.max_context_chars,
                settings.condensed_summary_chars,
            ),
            verifier=verifier,
            checkpoint_manager=checkpoint_manager,
        )

    def run(self, task: str) -> AgentResult:
        """执行一条自然语言编程任务。"""
        task = task.strip()
        if not task:
            return AgentResult(False, "任务不能为空。", 0)
        return self.loop.run(self.session, task)

    def reset_session(self) -> None:
        """显式清除连续对话历史。"""
        self.session.reset()
