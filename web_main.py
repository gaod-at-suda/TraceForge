"""TraceForge Web UI 启动入口。

示例：
    python web_main.py
    python web_main.py --workspace D:\\Projects\\my_project
    python web_main.py --port 8765

API Key 可从系统环境变量或项目根目录 .env 读取，且不会发送到浏览器。
"""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path
from threading import Timer

from traceforge.bootstrap import build_runtime
from traceforge.config.env_loader import load_env_file
from traceforge.web import run_web_console


def _default_workspace() -> Path:
    """优先使用显式环境变量，其次 demo_project，最后当前目录。"""
    configured = os.getenv("TRACEFORGE_WORKSPACE", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    demo = Path.cwd() / "demo_project"
    if demo.is_dir():
        return demo.resolve()

    return Path.cwd().resolve()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="启动 TraceForge 本地 Web Agent。",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=_default_workspace(),
        help="Agent 可读写的项目根目录；默认优先使用 ./demo_project。",
    )
    parser.add_argument("--host", default="127.0.0.1", help="监听地址。")
    parser.add_argument("--port", type=int, default=8765, help="监听端口。")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="启动后不自动打开浏览器。",
    )
    return parser.parse_args()


def main() -> int:
    env_path = load_env_file()
    args = _parse_args()
    workspace = args.workspace.expanduser().resolve()
    if not workspace.is_dir():
        print(f"[ERROR] Workspace 不存在或不是目录：{workspace}", file=sys.stderr)
        return 2

    try:
        runtime = build_runtime(str(workspace), enable_console_log=False)
    except Exception as exc:
        print(f"[ERROR] TraceForge 初始化失败：{exc}", file=sys.stderr)
        print("请在项目根目录 .env 或系统环境变量中配置 TRACEFORGE_API_KEY / TRACEFORGE_MODEL / TRACEFORGE_BASE_URL。", file=sys.stderr)
        return 2

    browser_host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    url = f"http://{browser_host}:{args.port}"

    print("=" * 72)
    print("TraceForge Web Agent")
    print("=" * 72)
    print(f"Workspace : {workspace}")
    print(f"Model     : {runtime.settings.model_name}")
    print(f"Mode      : {runtime.settings.agent_mode}")
    print(f"Web       : {url}")
    print(f"Config    : {env_path if env_path else '系统环境变量 / 默认值'}")
    print("提示：网页只提交自然语言任务，API Key 始终保留在 Python 后端。")
    print()

    if not args.no_browser:
        Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        run_web_console(runtime, args.host, args.port)
    except OSError as exc:
        print(f"[ERROR] 无法启动 Web Server：{exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
