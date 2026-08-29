"""TraceForge 原始 CLI 入口。

支持 CLI 连续对话、一次性任务和本地 Web Console 三种使用方式。
"""

from __future__ import annotations

import argparse
import sys

from traceforge.bootstrap import build_runtime
from traceforge.config.constants import DEFAULT_WEB_HOST, DEFAULT_WEB_PORT
from traceforge.config.env_loader import load_env_file
from traceforge.ui.console import ConsoleUI
from traceforge.web import run_web_console


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TraceForge：轻量级本地 Coding Agent")
    parser.add_argument("workspace", help="Agent 可以操作的项目目录")
    parser.add_argument("task", nargs="?", help="可选：一次性编程任务")
    parser.add_argument("--web", action="store_true", help="启动本地可视化 Web Console")
    parser.add_argument("--host", default=DEFAULT_WEB_HOST, help="Web Console 监听地址")
    parser.add_argument("--port", type=int, default=DEFAULT_WEB_PORT, help="Web Console 端口")
    parser.add_argument("--new-session", action="store_true", help="启动后先清空历史会话")
    return parser.parse_args()


def main() -> int:
    """加载本地配置后启动 CLI、单次任务或 Web Console。"""
    load_env_file()
    args = parse_args()
    ui = ConsoleUI()

    try:
        runtime = build_runtime(args.workspace, enable_console_log=not args.web)
    except Exception as exc:
        ui.error(f"初始化失败：{exc}")
        return 1

    if args.new_session:
        runtime.agent.reset_session()

    if args.web:
        run_web_console(runtime, args.host, args.port)
        return 0

    if args.task:
        result = runtime.agent.run(args.task)
        ui.final(result.message)
        return 0 if result.success else 1

    ui.welcome(args.workspace)
    ui.info("多轮会话已启用；输入 /reset 可清除历史，exit/quit 退出。")
    while True:
        try:
            task = ui.read_task()
        except (EOFError, KeyboardInterrupt):
            ui.info("已退出 TraceForge。")
            break

        if not task:
            continue
        if task.lower() in {"exit", "quit", "/exit", "/quit"}:
            ui.info("已退出 TraceForge。")
            break
        if task.lower() == "/reset":
            runtime.agent.reset_session()
            ui.info("会话历史已重置。")
            continue

        result = runtime.agent.run(task)
        ui.final(result.message)

    return 0


if __name__ == "__main__":
    sys.exit(main())
