"""CLI EventBus 事件渲染器。"""

from __future__ import annotations

from traceforge.events.models import AgentEvent


class AgentLogger:
    """把关键生命周期事件格式化到终端。"""

    def on_event(self, event: AgentEvent) -> None:
        kind = event.event_type
        data = event.data

        if kind == "run_started":
            print(
                f"[RUN] mode={data.get('mode')} "
                f"checkpoint={data.get('checkpoint_enabled')}"
            )
        elif kind == "step_started":
            print(f"\n[AGENT] Step {event.step}/{data.get('max_steps')}")
        elif kind == "tool_started":
            print(f"[TOOL] {data.get('tool')} args={data.get('arguments')}")
        elif kind == "tool_finished":
            output = data.get("output", "")
            preview = output if len(output) <= 1200 else output[:1200] + "\n..."
            print(f"[RESULT] {data.get('duration_ms')} ms\n{preview}")
        elif kind == "tool_failed":
            print(f"[ERROR] {data.get('tool')}: {data.get('error')}")
        elif kind == "file_changed":
            print(f"[DIFF] {data.get('path')} 已发生修改")
        elif kind == "verification_started":
            print("[VERIFY] 宿主程序开始自动验证...")
        elif kind == "verification_finished":
            status = "PASS" if data.get("success") else "FAIL"
            print(f"[VERIFY {status}] {data.get('command') or data.get('reason')}")
            if not data.get("success"):
                print(data.get("output", ""))
        elif kind == "acceptance_failed":
            print(f"[ACCEPTANCE FAIL] {data.get('reason', '最终验收失败')}")
        elif kind == "rollback_started":
            revision = str(data.get("revision") or "")[:12]
            print(f"[ROLLBACK] 正在恢复 Git Checkpoint {revision}...")
        elif kind == "rollback_finished":
            status = "PASS" if data.get("success") else "FAIL"
            revision = str(data.get("revision") or "")[:12]
            print(f"[ROLLBACK {status}] revision={revision}")
