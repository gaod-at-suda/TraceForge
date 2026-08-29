"""TraceForge V1 核心 Agent Loop。

保持单层可解释闭环：
LLM 决策 -> Tool -> Observation -> LLM。
V3 在闭环外围增加 Git Checkpoint 和宿主侧 Automatic Verification，
但不把这些机制交给模型自行决定。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from traceforge.config.settings import Settings
from traceforge.events.bus import EventBus
from traceforge.git import GitCheckpoint, GitCheckpointManager
from traceforge.session.session import Session
from traceforge.tools.registry import ToolRegistry
from traceforge.verification import Verifier

from .context import ContextManager
from .result import AgentResult

if TYPE_CHECKING:
    from traceforge.llm.client import LLMClient
else:
    LLMClient = Any


_FINALIZATION_PROMPT = """\
FINALIZATION MODE — tool execution is now closed.
You have reached TraceForge's normal tool-step limit. Do not request or describe any new
commands, file reads, edits, cleanup, or verification. Based only on the work and evidence
already present in the conversation, give the final user-facing answer now.

If the task is complete, concisely summarize what changed and how it was verified.
If the task is not complete, clearly state what remains unresolved. Match the user's language.
"""


class AgentLoop:
    """执行一次完整编程任务。"""

    def __init__(
        self,
        llm: LLMClient,
        tool_registry: ToolRegistry,
        settings: Settings,
        event_bus: EventBus,
        context_manager: ContextManager,
        verifier: Verifier,
        checkpoint_manager: GitCheckpointManager,
    ) -> None:
        self.llm = llm
        self.tool_registry = tool_registry
        self.settings = settings
        self.event_bus = event_bus
        self.context_manager = context_manager
        self.verifier = verifier
        self.checkpoint_manager = checkpoint_manager

    def run(self, session: Session, task: str) -> AgentResult:
        run_id = uuid4().hex[:12]
        self.tool_registry.reset_run_state()
        checkpoint = self.checkpoint_manager.create()
        session.add_user(task)

        self.event_bus.emit(
            "run_started",
            run_id,
            data={
                "task": task,
                "mode": self.settings.agent_mode,
                "checkpoint_enabled": checkpoint.enabled,
                "checkpoint_revision": checkpoint.revision,
                "checkpoint_reason": checkpoint.reason,
            },
        )

        verification_failures = 0

        for step in range(1, self.settings.max_steps + 1):
            self.event_bus.emit(
                "step_started",
                run_id,
                step=step,
                data={"max_steps": self.settings.max_steps},
            )

            messages = self.context_manager.build(session.messages)
            self.event_bus.emit(
                "model_started",
                run_id,
                step=step,
                data={"message_count": len(messages)},
            )

            try:
                response = self.llm.chat(messages, self.tool_registry.schemas)
            except Exception as exc:
                return self._fail(
                    run_id,
                    step,
                    f"模型调用失败：{exc}",
                    checkpoint=checkpoint,
                )

            session.add_assistant_response(response)
            self.event_bus.emit(
                "model_finished",
                run_id,
                step=step,
                data={
                    "content": response.content or "",
                    "tool_call_count": len(response.tool_calls),
                },
            )

            if not response.tool_calls:
                verification = self._verify_if_needed(run_id, step)

                if verification and not verification.success:
                    verification_failures += 1
                    if verification_failures <= self.settings.verification_retries:
                        session.add_user(
                            "HOST AUTOMATIC VERIFICATION FAILED.\n"
                            "Please diagnose the real test output below, repair the project, "
                            "and verify again before finishing.\n\n"
                            f"Command: {verification.command}\n"
                            f"Output:\n{verification.output}"
                        )
                        continue
                    return self._fail(
                        run_id,
                        step,
                        "宿主侧自动验证连续失败，已达到修复重试上限。",
                        checkpoint=checkpoint,
                    )

                final_text = response.content or "任务已结束，但模型未返回总结。"
                self.event_bus.emit(
                    "run_finished",
                    run_id,
                    step=step,
                    data={
                        "message": final_text,
                        "checkpoint_revision": checkpoint.revision,
                    },
                )
                return AgentResult(True, final_text, step, run_id)

            self._execute_tool_calls(run_id, step, session, response.tool_calls)

        # 正常工具预算耗尽时，不立即把“其实已经完成、只差总结”的任务判失败。
        # 先由宿主验证当前真实工作区；验证通过后仅额外允许一次“无工具收尾”。
        return self._finalize_after_step_limit(
            run_id=run_id,
            session=session,
            checkpoint=checkpoint,
        )

    def _finalize_after_step_limit(
        self,
        run_id: str,
        session: Session,
        checkpoint: GitCheckpoint,
    ) -> AgentResult:
        step = self.settings.max_steps
        verification = self._verify_if_needed(run_id, step)

        if verification and not verification.success:
            return self._fail(
                run_id,
                step,
                (
                    f"达到最大执行步数 {self.settings.max_steps}，且宿主侧最终验证未通过。"
                    f"\n验证命令：{verification.command}\n{verification.output}"
                ),
                event_type="run_stopped",
                checkpoint=checkpoint,
            )

        self.event_bus.emit(
            "finalization_started",
            run_id,
            step=step,
            data={
                "reason": "已达到工具执行步数上限，进入一次无工具收尾",
                "tool_access": False,
                "verification_passed": None if verification is None else verification.success,
            },
        )

        messages = self.context_manager.build(session.messages)
        messages = [*messages, {"role": "user", "content": _FINALIZATION_PROMPT}]
        self.event_bus.emit(
            "model_started",
            run_id,
            step=step,
            data={"message_count": len(messages), "finalization": True},
        )

        try:
            response = self.llm.chat(messages, None)
        except Exception as exc:
            return self._fail(
                run_id,
                step,
                f"达到最大执行步数后，无工具收尾调用失败：{exc}",
                event_type="run_stopped",
                checkpoint=checkpoint,
            )

        session.add_assistant_response(response)
        self.event_bus.emit(
            "model_finished",
            run_id,
            step=step,
            data={
                "content": response.content or "",
                "tool_call_count": len(response.tool_calls),
                "finalization": True,
            },
        )

        if response.tool_calls:
            return self._fail(
                run_id,
                step,
                "达到最大执行步数后模型仍请求工具调用，无法安全完成收尾。",
                event_type="run_stopped",
                checkpoint=checkpoint,
            )

        final_text = (response.content or "").strip()
        if not final_text:
            return self._fail(
                run_id,
                step,
                "达到最大执行步数后模型未返回有效最终总结。",
                event_type="run_stopped",
                checkpoint=checkpoint,
            )

        self.event_bus.emit(
            "finalization_finished",
            run_id,
            step=step,
            data={"success": True, "message": final_text},
        )
        self.event_bus.emit(
            "run_finished",
            run_id,
            step=step,
            data={
                "message": final_text,
                "checkpoint_revision": checkpoint.revision,
                "finalization_grace": True,
            },
        )
        return AgentResult(True, final_text, step, run_id)

    def _execute_tool_calls(self, run_id: str, step: int, session: Session, calls) -> None:
        for call in calls:
            self.event_bus.emit(
                "tool_started",
                run_id,
                step=step,
                data={"tool": call.name, "arguments": call.arguments},
            )

            result = self.tool_registry.execute(call.name, call.arguments)
            session.add_tool_result(call.id, call.name, result.to_model_text())

            self.event_bus.emit(
                "tool_finished" if result.success else "tool_failed",
                run_id,
                step=step,
                data={
                    "tool": call.name,
                    "success": result.success,
                    "output": result.output,
                    "error": result.error,
                    "duration_ms": round(result.duration_ms, 2),
                    "metadata": result.metadata,
                },
            )

            if result.metadata.get("diff"):
                self.event_bus.emit(
                    "file_changed",
                    run_id,
                    step=step,
                    data={
                        "path": result.metadata.get("path"),
                        "diff": result.metadata.get("diff"),
                    },
                )

    def _verify_if_needed(self, run_id: str, step: int):
        """只在本次任务实际修改过文件时执行宿主自动验证。"""
        if self.tool_registry.mutation_count == 0:
            return None

        self.event_bus.emit("verification_started", run_id, step=step)
        result = self.verifier.verify()
        self.event_bus.emit(
            "verification_finished",
            run_id,
            step=step,
            data={
                "detected": result.detected,
                "success": result.success,
                "command": result.command,
                "reason": result.reason,
                "return_code": result.return_code,
                "output": result.output,
            },
        )
        return result

    def _fail(
        self,
        run_id: str,
        step: int,
        message: str,
        event_type: str = "run_failed",
        checkpoint: GitCheckpoint | None = None,
    ) -> AgentResult:
        """失败退出；若本轮产生过修改且有安全基线，则自动回滚。"""
        rollback_attempted = False
        rollback_success: bool | None = None

        if (
            checkpoint is not None
            and checkpoint.enabled
            and bool(checkpoint.revision)
            and self.tool_registry.mutation_count > 0
        ):
            rollback_attempted = True
            self.event_bus.emit(
                "rollback_started",
                run_id,
                step=step,
                data={
                    "revision": checkpoint.revision,
                    "reason": "Agent 运行失败，恢复任务开始前的干净 Git 基线",
                },
            )
            rollback_success = self.checkpoint_manager.rollback(checkpoint)
            self.event_bus.emit(
                "rollback_finished",
                run_id,
                step=step,
                data={
                    "success": rollback_success,
                    "revision": checkpoint.revision,
                },
            )

            if rollback_success:
                message += "\n已自动回滚到任务开始前的 Git Checkpoint。"
            else:
                message += "\n警告：自动回滚失败，请人工检查当前工作区。"

        self.event_bus.emit(
            event_type,
            run_id,
            step=step,
            data={
                "error": message,
                "message": message,
                "rollback_attempted": rollback_attempted,
                "rollback_success": rollback_success,
            },
        )
        return AgentResult(False, message, step, run_id)
