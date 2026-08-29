"""TraceForge 运行时组装。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from traceforge.agent.agent import CodingAgent
from traceforge.config.settings import Settings
from traceforge.events import EventBus, InMemoryEventStore
from traceforge.git import GitCheckpointManager
from traceforge.observability import TraceRecorder
from traceforge.session import Session, SessionStore
from traceforge.tools.registry import ToolRegistry
from traceforge.ui.logger import AgentLogger
from traceforge.verification import Verifier
from traceforge.workspace.workspace import Workspace


@dataclass
class RuntimeBundle:
    """保存一次 TraceForge 运行所需的核心组件。"""

    agent: CodingAgent
    event_bus: EventBus
    event_store: InMemoryEventStore
    workspace: Workspace
    settings: Settings
    verifier: Verifier
    checkpoint_manager: GitCheckpointManager


def build_runtime(
    workspace_path: str,
    enable_console_log: bool = True,
) -> RuntimeBundle:
    """创建 Agent、Session、EventBus、验证器和 Checkpoint。"""
    settings = Settings.from_env()
    workspace = Workspace(workspace_path)

    event_bus = EventBus()
    event_store = InMemoryEventStore()
    event_bus.subscribe(event_store.on_event)
    event_bus.subscribe(TraceRecorder(settings.runtime_dir / "traces").on_event)
    if enable_console_log:
        event_bus.subscribe(AgentLogger().on_event)

    workspace_id = hashlib.sha1(
        str(workspace.root).encode("utf-8")
    ).hexdigest()[:12]
    session = Session(
        SessionStore(
            settings.runtime_dir / "sessions" / f"{workspace_id}.jsonl"
        )
    )

    # 延迟导入模型客户端，使纯本地单元测试无需初始化线上 API 客户端。
    from traceforge.llm.client import LLMClient

    registry = ToolRegistry(workspace, settings)
    verifier = Verifier(
        workspace,
        timeout=max(settings.command_timeout * 2, 60),
    )
    checkpoint_manager = GitCheckpointManager(workspace)

    agent = CodingAgent(
        llm=LLMClient(settings),
        tool_registry=registry,
        settings=settings,
        event_bus=event_bus,
        session=session,
        verifier=verifier,
        checkpoint_manager=checkpoint_manager,
    )
    return RuntimeBundle(
        agent,
        event_bus,
        event_store,
        workspace,
        settings,
        verifier,
        checkpoint_manager,
    )
