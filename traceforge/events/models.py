"""Agent 生命周期事件数据结构。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import time
from typing import Any


@dataclass(frozen=True)
class AgentEvent:
    """描述 Agent 运行过程中的一个可观察事件。"""

    seq: int
    event_type: str
    run_id: str
    step: int | None
    data: dict[str, Any]
    timestamp: float

    @classmethod
    def create(
        cls,
        seq: int,
        event_type: str,
        run_id: str,
        step: int | None = None,
        data: dict[str, Any] | None = None,
    ) -> "AgentEvent":
        return cls(
            seq=seq,
            event_type=event_type,
            run_id=run_id,
            step=step,
            data=data or {},
            timestamp=time(),
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为可直接序列化成 JSON 的字典。"""
        return asdict(self)
