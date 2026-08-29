"""零额外依赖的本地 Web Console。

使用延迟导入，避免仅测试 WebState 时提前加载完整 Agent/LLM 运行时。
"""

from __future__ import annotations


def run_web_console(*args, **kwargs):
    """延迟加载真正的 Web Server 实现。"""
    from .server import run_web_console as _run_web_console

    return _run_web_console(*args, **kwargs)


__all__ = ["run_web_console"]
