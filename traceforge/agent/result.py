"""Agent 运行结果数据结构。"""

from dataclasses import dataclass


@dataclass
class AgentResult:
    """表示一次用户任务的最终执行结果。"""

    success: bool
    message: str
    steps: int
    run_id: str = ""
