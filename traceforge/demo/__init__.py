"""一键自动测试模块。

该模块只负责测试/演示流程，不参与 Agent 的核心决策逻辑。
"""

from .runner import run_direct_test

__all__ = ["run_direct_test"]
