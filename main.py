"""TraceForge 一键验收入口。

运行 ``python main.py`` 后，程序会自动执行框架测试、重建 Demo Workspace、
建立 Git 基线、调用真实 Coding Agent、执行宿主侧验证，并生成 Diff、Trace 与 HTML 报告。
整个流程由预设场景驱动，无需交互式输入任务。
"""

from __future__ import annotations

import sys

from traceforge.config.env_loader import load_env_file
from traceforge.demo.runner import run_direct_test


def main() -> int:
    """加载本地配置并执行完整的一键 Agent 测试流程。"""
    load_env_file()
    return run_direct_test()


if __name__ == "__main__":
    sys.exit(main())
