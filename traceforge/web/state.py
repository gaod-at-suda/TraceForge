"""Web Console 运行状态。

浏览器提交任务后由后台线程调用同一个 CodingAgent；前端通过事件轮询观察进度。
成功任务若建立了安全 Git Checkpoint，还可以在工作区未被再次修改的前提下
从 Web UI 显式恢复本次 Agent 产生的改动。
"""

from __future__ import annotations

from threading import Lock, Thread

from traceforge.agent.agent import CodingAgent
from traceforge.agent.result import AgentResult
from traceforge.events.bus import EventBus
from traceforge.events.store import InMemoryEventStore
from traceforge.git import GitCheckpoint, GitCheckpointManager


class WebState:
    """线程安全地管理单实例 Agent 的 Web 运行状态。"""

    def __init__(
        self,
        agent: CodingAgent,
        event_store: InMemoryEventStore,
        checkpoint_manager: GitCheckpointManager | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.agent = agent
        self.event_store = event_store
        self.checkpoint_manager = checkpoint_manager
        self.event_bus = event_bus
        self._lock = Lock()
        self.running = False
        self.latest_result: AgentResult | None = None
        self._restore_checkpoint: GitCheckpoint | None = None
        self._restore_fingerprint: str | None = None
        self._restore_used = False
        self._restore_reason = "完成一次带安全 Git Checkpoint 的修改任务后可用。"

    def start_task(self, task: str) -> bool:
        """后台执行任务；已经运行时拒绝重复启动。"""
        with self._lock:
            if self.running:
                return False
            self.running = True
            self.latest_result = None
            self._clear_restore_state()
            self.event_store.clear()

        Thread(target=self._worker, args=(task,), daemon=True).start()
        return True

    def _worker(self, task: str) -> None:
        """执行后台任务，并保证异常也能反映到 Web 状态。"""
        try:
            result = self.agent.run(task)
        except Exception as exc:  # Agent 边界之外的意外错误仍应在 UI 中可见。
            result = AgentResult(False, f"Web 后台任务异常：{exc}", 0)

        restore_checkpoint, restore_fingerprint, restore_reason = self._build_restore_state(result)
        with self._lock:
            self.latest_result = result
            self._restore_checkpoint = restore_checkpoint
            self._restore_fingerprint = restore_fingerprint
            self._restore_reason = restore_reason
            self.running = False

    def _build_restore_state(
        self,
        result: AgentResult,
    ) -> tuple[GitCheckpoint | None, str | None, str]:
        """根据本轮事件和 Git 状态建立可供用户显式恢复的安全凭据。"""
        manager = self.checkpoint_manager
        if manager is None:
            return None, None, "当前 Web Runtime 未配置 Git Checkpoint。"
        if not result.success or not result.run_id:
            return None, None, "仅成功完成且保留修改的任务支持手动恢复。"

        run_started = None
        for event in self.event_store.after(0):
            if event.get("run_id") == result.run_id and event.get("event_type") == "run_started":
                run_started = event
                break
        if run_started is None:
            return None, None, "未找到本次任务的 Git Checkpoint 信息。"

        data = run_started.get("data") or {}
        checkpoint = GitCheckpoint(
            enabled=bool(data.get("checkpoint_enabled")),
            revision=str(data.get("checkpoint_revision") or ""),
            reason=str(data.get("checkpoint_reason") or ""),
        )
        if not checkpoint.enabled or not checkpoint.revision:
            return None, None, checkpoint.reason or "本次任务未建立可恢复的 Git Checkpoint。"

        differs = manager.differs_from(checkpoint)
        if differs is None:
            return None, None, "无法确认当前 Git 工作区状态，已禁用手动恢复。"
        if not differs:
            return None, None, "本次任务结束后工作区与任务开始前一致，无需恢复。"

        fingerprint = manager.worktree_fingerprint()
        if fingerprint is None:
            return None, None, "无法生成任务结束后的工作区指纹，已禁用手动恢复。"

        return checkpoint, fingerprint, "可恢复到本次任务开始前的 Git Checkpoint。"

    def restore_last_run(self) -> tuple[bool, str]:
        """恢复最近一次成功任务的修改，并拒绝覆盖任务结束后的新增人工改动。"""
        with self._lock:
            if self.running:
                return False, "Agent 正在运行，任务结束后才能恢复。"
            if self._restore_used:
                return False, "本次任务修改已经恢复。"
            checkpoint = self._restore_checkpoint
            fingerprint = self._restore_fingerprint
            manager = self.checkpoint_manager
            result = self.latest_result
            if checkpoint is None or fingerprint is None or manager is None or result is None:
                return False, self._restore_reason

            current_fingerprint = manager.worktree_fingerprint()
            if current_fingerprint is None:
                return False, "无法确认当前工作区状态，为避免误删文件，已拒绝恢复。"
            if current_fingerprint != fingerprint:
                return (
                    False,
                    "任务结束后工作区又发生了变化。为避免覆盖新的人工修改，已拒绝自动恢复；请先处理当前 Git 变更。",
                )

            if self.event_bus is not None:
                self.event_bus.emit(
                    "manual_restore_started",
                    result.run_id,
                    data={
                        "revision": checkpoint.revision,
                        "reason": "用户从 Web UI 请求恢复本次 Agent 修改",
                    },
                )

            success = manager.rollback(checkpoint)
            message = (
                "已恢复到本次任务开始前的 Git Checkpoint，并清除本次任务产生的未跟踪文件。"
                if success
                else "恢复失败，请检查 Git 状态后再处理当前工作区。"
            )

            if success:
                # 工作区已经回到旧状态，清除会话可避免下一轮模型继续依赖已撤销的修改。
                self.agent.reset_session()
                self._restore_used = True
                self._restore_checkpoint = None
                self._restore_fingerprint = None
                self._restore_reason = message

            if self.event_bus is not None:
                self.event_bus.emit(
                    "manual_restore_finished",
                    result.run_id,
                    data={
                        "success": success,
                        "revision": checkpoint.revision,
                        "message": message,
                    },
                )
            return success, message

    def reset_session(self) -> bool:
        """仅在未运行任务时允许清空会话和当前 Web 展示状态。"""
        with self._lock:
            if self.running:
                return False
            self.agent.reset_session()
            self.event_store.clear()
            self.latest_result = None
            self._clear_restore_state()
            return True

    def _clear_restore_state(self) -> None:
        self._restore_checkpoint = None
        self._restore_fingerprint = None
        self._restore_used = False
        self._restore_reason = "完成一次带安全 Git Checkpoint 的修改任务后可用。"

    def status(self) -> dict:
        """返回用于 Web API 的一致状态快照。"""
        with self._lock:
            running = self.running
            result = self.latest_result
            restore_available = (
                not running
                and not self._restore_used
                and self._restore_checkpoint is not None
                and self._restore_fingerprint is not None
            )
            restore = {
                "available": restore_available,
                "used": self._restore_used,
                "reason": self._restore_reason,
            }

        return {
            "running": running,
            "result": None
            if result is None
            else {
                "success": result.success,
                "message": result.message,
                "steps": result.steps,
                "run_id": result.run_id,
            },
            "restore": restore,
        }
