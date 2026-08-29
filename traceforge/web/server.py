"""基于 Python 标准库的本地 Web Console Server。

不引入 Flask/FastAPI 等额外 Web 框架，减少项目依赖和答辩解释成本。
"""

from __future__ import annotations

import json
import os
import string
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock
from urllib.parse import parse_qs, urlparse

from traceforge.bootstrap import RuntimeBundle, build_runtime

from .state import WebState

STATIC_DIR = Path(__file__).with_name("static")


class WebRuntimeContext:
    """保存可切换 Workspace 的 Web 运行时。

    切换工作区时重建 RuntimeBundle，因此 Workspace sandbox、Session、Verifier、
    Git Checkpoint 与 ToolRegistry 都会绑定到新的项目根目录，而不是只修改 UI 文本。
    """

    def __init__(self, runtime: RuntimeBundle) -> None:
        self._lock = RLock()
        self._runtime = runtime
        self._state = WebState(runtime.agent, runtime.event_store)

    def status(self) -> dict:
        with self._lock:
            payload = self._state.status()
            payload.update(
                {
                    "workspace": str(self._runtime.workspace.root),
                    "model": self._runtime.settings.model_name,
                    "mode": self._runtime.settings.agent_mode,
                }
            )
            return payload

    def events_after(self, after: int) -> list[dict]:
        with self._lock:
            return self._state.event_store.after(after)

    def start_task(self, task: str) -> bool:
        with self._lock:
            return self._state.start_task(task)

    def reset_session(self) -> bool:
        with self._lock:
            return self._state.reset_session()

    def switch_workspace(self, path_text: str) -> tuple[bool, str]:
        """切换到用户明确选择的本地目录。运行中禁止切换。"""
        with self._lock:
            if self._state.running:
                return False, "Agent 正在运行，任务结束后才能切换工作区。"

            try:
                target = Path(path_text).expanduser().resolve()
            except (OSError, RuntimeError) as exc:
                return False, f"无法解析工作区路径：{exc}"

            if not target.is_dir():
                return False, f"目录不存在或不是文件夹：{target}"

            try:
                runtime = build_runtime(str(target), enable_console_log=False)
            except Exception as exc:
                return False, f"工作区初始化失败：{exc}"

            self._runtime = runtime
            self._state = WebState(runtime.agent, runtime.event_store)
            return True, str(target)

    def current_workspace(self) -> Path:
        with self._lock:
            return self._runtime.workspace.root


class ConsoleHandler(BaseHTTPRequestHandler):
    """处理静态页面和少量 JSON API。"""

    context: WebRuntimeContext

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/events":
            query = parse_qs(parsed.query)
            try:
                after = int(query.get("after", ["0"])[0])
            except ValueError:
                after = 0
            return self._json({"events": self.context.events_after(after)})

        if parsed.path == "/api/status":
            return self._json(self.context.status())

        if parsed.path == "/api/directories":
            query = parse_qs(parsed.query)
            path_text = query.get("path", [""])[0].strip()
            try:
                payload = self._directory_listing(path_text)
            except (OSError, PermissionError) as exc:
                return self._json({"ok": False, "error": f"无法读取目录：{exc}"}, 400)
            return self._json(payload)

        if parsed.path in {"/", "/index.html"}:
            return self._static("index.html", "text/html; charset=utf-8")
        if parsed.path == "/app.js":
            return self._static("app.js", "text/javascript; charset=utf-8")
        if parsed.path == "/style.css":
            return self._static("style.css", "text/css; charset=utf-8")
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/api/run":
            data = self._read_json()
            task = str(data.get("task", "")).strip()
            if not task:
                return self._json({"ok": False, "error": "任务不能为空"}, 400)
            if not self.context.start_task(task):
                return self._json({"ok": False, "error": "Agent 正在运行"}, 409)
            return self._json({"ok": True})

        if parsed.path == "/api/reset":
            if not self.context.reset_session():
                return self._json({"ok": False, "error": "运行中无法重置"}, 409)
            return self._json({"ok": True})

        if parsed.path == "/api/workspace":
            data = self._read_json()
            path_text = str(data.get("path", "")).strip()
            if not path_text:
                return self._json({"ok": False, "error": "工作区路径不能为空"}, 400)
            ok, message = self.context.switch_workspace(path_text)
            if not ok:
                return self._json({"ok": False, "error": message}, 409)
            payload = self.context.status()
            payload.update({"ok": True, "message": "工作区已切换"})
            return self._json(payload)

        self.send_error(404)

    def _directory_listing(self, path_text: str) -> dict:
        """返回文件夹浏览器所需的根目录、父目录与一级子目录。"""
        current = self.context.current_workspace()
        target = Path(path_text).expanduser() if path_text else current
        target = target.resolve()
        if not target.is_dir():
            raise OSError(f"目录不存在：{target}")

        children: list[dict[str, str]] = []
        try:
            entries = list(target.iterdir())
        except PermissionError:
            raise

        directories = [entry for entry in entries if entry.is_dir()]
        directories.sort(key=lambda p: (p.name.startswith("."), p.name.casefold()))
        truncated = len(directories) > 250
        for child in directories[:250]:
            children.append({"name": child.name, "path": str(child)})

        roots: list[str] = []
        if os.name == "nt":
            for letter in string.ascii_uppercase:
                root = Path(f"{letter}:\\")
                if root.exists():
                    roots.append(str(root))
        else:
            roots.append("/")

        parent = target.parent
        return {
            "ok": True,
            "current": str(target),
            "parent": None if parent == target else str(parent),
            "roots": roots,
            "children": children,
            "truncated": truncated,
        }

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _static(self, filename: str, content_type: str) -> None:
        path = STATIC_DIR / filename
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        # 避免轮询 API 每次请求都刷屏，Agent 事件本身已经有 CLI Trace。
        return


def run_web_console(
    runtime: RuntimeBundle,
    host: str,
    port: int,
) -> None:
    """启动阻塞式本地 Web Server。"""
    context = WebRuntimeContext(runtime)

    class BoundHandler(ConsoleHandler):
        pass

    BoundHandler.context = context
    server = ThreadingHTTPServer((host, port), BoundHandler)
    print(f"TraceForge Web Console: http://{host}:{port}")
    print("网页中可以切换本地 Workspace；切换后会创建独立运行时和会话。")
    print("按 Ctrl+C 结束服务。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
