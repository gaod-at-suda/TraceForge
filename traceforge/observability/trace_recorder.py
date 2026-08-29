"""把 Agent 生命周期事件保存为 JSONL Trace。"""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

from traceforge.events.models import AgentEvent


class TraceRecorder:
    """每个 run_id 使用一个独立 Trace 文件。"""

    def __init__(self, trace_dir: Path) -> None:
        self.trace_dir = trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def on_event(self, event: AgentEvent) -> None:
        path = self.trace_dir / f"{event.run_id}.jsonl"
        with self._lock, path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
