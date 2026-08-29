"""TraceForge 自定义异常。

使用明确的异常类型，可以让 Agent Loop 更容易区分错误来源，
也便于后续测试和答辩时解释错误处理机制。
"""


class TraceForgeError(Exception):
    """TraceForge 所有自定义异常的基类。"""


class WorkspaceSecurityError(TraceForgeError):
    """访问工作区之外路径时抛出。"""


class ToolExecutionError(TraceForgeError):
    """工具执行失败时抛出。"""


class CommandTimeoutError(ToolExecutionError):
    """本地命令执行超时时抛出。"""
