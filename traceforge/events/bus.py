"""轻量级 EventBus。

Agent 核心只负责发布事件，CLI、Web Console、Trace Recorder 等展示/记录模块
通过订阅事件工作，从而避免 UI 逻辑侵入 Agent Loop。
"""

from __future__ import annotations

from threading import RLock
from typing import Callable

from .models import AgentEvent

EventListener = Callable[[AgentEvent], None]


class EventBus:
    """线程安全的同步事件总线。"""

    def __init__(self) -> None:
        self._listeners: list[EventListener] = []
        self._seq = 0
        self._lock = RLock()

    def subscribe(self, listener: EventListener) -> None:
        """注册事件监听器。"""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def emit(
        self,
        event_type: str,
        run_id: str,
        step: int | None = None,
        data: dict | None = None,
    ) -> AgentEvent:
        """创建事件并广播给当前所有监听器。"""
        with self._lock:
            self._seq += 1
            event = AgentEvent.create(
                seq=self._seq,
                event_type=event_type,
                run_id=run_id,
                step=step,
                data=data,
            )
            listeners = list(self._listeners)

        # 事件监听器属于可观测性旁路；单个监听器异常不得影响 Agent 主执行流程。
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                continue
        return event
