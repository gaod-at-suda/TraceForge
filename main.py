"""TraceForge 一键自动测试入口。

TraceForge 默认通过 PyCharm 直接 Run 运行预设 Coding Agent 测试场景。

在 PyCharm 中直接点击 Run 即可：
1. 自动重置 demo_project；
2. 自动运行 TraceForge 自身单元测试；
3. 自动运行 demo_project 基线测试；
4. 自动执行预设 Coding Agent 任务；
5. 自动再次运行 pytest 验证 Agent 修改结果；
6. 自动生成可视化 HTML 测试报告。

整个流程不需要用户在命令行中输入自然语言指令。
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
