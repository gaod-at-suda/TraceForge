"""Web Console 运行状态。

浏览器提交任务后由后台线程调用同一个 CodingAgent；前端通过事件轮询观察进度。
"""

from __future__ import annotations

from threading import Lock, Thread

from traceforge.agent.agent import CodingAgent
from traceforge.agent.result import AgentResult
from traceforge.events.store import InMemoryEventStore


class WebState:
    """管理单实例 Agent 的 Web 运行状态。"""

    def __init__(self, agent: CodingAgent, event_store: InMemoryEventStore) -> None:
        self.agent = agent
        self.event_store = event_store
        self._lock = Lock()
        self.running = False
        self.latest_result: AgentResult | None = None

    def start_task(self, task: str) -> bool:
        """后台执行任务；已经运行时拒绝重复启动。"""
        with self._lock:
            if self.running:
                return False
            self.running = True
            self.latest_result = None
            self.event_store.clear()

        thread = Thread(target=self._worker, args=(task,), daemon=True)
        thread.start()
        return True

    def _worker(self, task: str) -> None:
        try:
            self.latest_result = self.agent.run(task)
        finally:
            with self._lock:
                self.running = False

    def reset_session(self) -> bool:
        """仅在未运行任务时允许清空会话。"""
        with self._lock:
            if self.running:
                return False
            self.agent.reset_session()
            self.event_store.clear()
            self.latest_result = None
            return True

    def status(self) -> dict:
        result = self.latest_result
        return {
            "running": self.running,
            "result": None
            if result is None
            else {
                "success": result.success,
                "message": result.message,
                "steps": result.steps,
                "run_id": result.run_id,
            },
        }
