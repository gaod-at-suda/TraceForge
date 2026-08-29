"""供 Web Console 查询的内存事件存储。"""

from __future__ import annotations

from threading import RLock

from .models import AgentEvent


class InMemoryEventStore:
    """保存最近一次/多次 Agent 运行产生的事件。"""

    def __init__(self, max_events: int = 5000) -> None:
        self.max_events = max_events
        self._events: list[AgentEvent] = []
        self._lock = RLock()

    def on_event(self, event: AgentEvent) -> None:
        """EventBus 监听器入口。"""
        with self._lock:
            self._events.append(event)
            if len(self._events) > self.max_events:
                self._events = self._events[-self.max_events :]

    def after(self, seq: int = 0) -> list[dict]:
        """返回序号大于 seq 的事件，供浏览器轮询。"""
        with self._lock:
            return [e.to_dict() for e in self._events if e.seq > seq]

    def clear(self) -> None:
        """清空当前展示事件，不影响磁盘 Trace。"""
        with self._lock:
            self._events.clear()
