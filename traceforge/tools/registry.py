"""工具注册中心和 Never-Throw 执行边界。"""

from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

from traceforge.codebase import glob_files, grep_search, repo_map
from traceforge.config.settings import Settings
from traceforge.edit import apply_patch
from traceforge.observability.diff_tracker import DiffTracker
from traceforge.policy import AgentMode, ToolPermissionPolicy
from traceforge.workspace.workspace import Workspace

from .command_tools import CommandPolicy, run_command
from .file_tools import list_directory, read_file, replace_in_file, write_file
from .result import ToolResult
from .schemas import TOOL_SCHEMA_BY_NAME


class ToolRegistry:
    """统一管理工具权限、Schema、本地执行、输出截断和 Diff。"""

    _FILE_MUTATION_TOOLS = {"write_file", "replace_in_file", "apply_patch"}

    def __init__(self, workspace: Workspace, settings: Settings) -> None:
        self.workspace = workspace
        self.settings = settings
        self.diff_tracker = DiffTracker(workspace)
        self.command_policy = CommandPolicy()
        self.permission_policy = ToolPermissionPolicy(
            AgentMode.parse(settings.agent_mode)
        )
        self.mutation_count = 0

        self._tools: dict[str, Callable[..., str]] = {
            "list_directory": self._list_directory,
            "read_file": self._read_file,
            "glob_files": self._glob_files,
            "grep_search": self._grep_search,
            "repo_map": self._repo_map,
            "write_file": self._write_file,
            "replace_in_file": self._replace_in_file,
            "apply_patch": self._apply_patch,
            "run_command": self._run_command,
        }

    @property
    def schemas(self) -> list[dict]:
        """按 AgentMode 过滤模型可见工具。"""
        return [
            TOOL_SCHEMA_BY_NAME[name]
            for name in self._tools
            if self.permission_policy.visible(name)
        ]

    def reset_run_state(self) -> None:
        """清除只属于本次任务的统计。"""
        self.mutation_count = 0

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """执行任意工具且永不向 Agent Loop 抛异常。"""
        started = perf_counter()
        metadata: dict[str, Any] = {}

        if "__raw_arguments__" in arguments:
            return self._failure(
                started,
                f"模型返回了无法解析的工具参数：{arguments['__raw_arguments__']}",
            )

        tool = self._tools.get(name)
        if tool is None:
            return self._failure(started, f"未知工具：{name}")

        permission = self.permission_policy.check(name)
        if not permission.allowed:
            return self._failure(started, f"权限策略拒绝执行：{permission.reason}")

        mutation_path = (
            arguments.get("path")
            if name in self._FILE_MUTATION_TOOLS
            else None
        )
        before: str | None = None
        if mutation_path:
            try:
                before = self.diff_tracker.snapshot(str(mutation_path))
            except Exception:
                before = None

        try:
            output = self._truncate(str(tool(**arguments)))

            if mutation_path:
                self.mutation_count += 1
                metadata["mutation"] = True
                metadata["path"] = str(mutation_path)
                metadata["diff"] = self._truncate(
                    self.diff_tracker.make_diff(str(mutation_path), before)
                )

            return ToolResult(
                success=True,
                output=output,
                duration_ms=(perf_counter() - started) * 1000,
                metadata=metadata,
            )
        except Exception as exc:
            return self._failure(started, f"{name} 执行失败：{exc}")

    def _failure(self, started: float, error: str) -> ToolResult:
        return ToolResult(
            success=False,
            error=error,
            duration_ms=(perf_counter() - started) * 1000,
        )

    def _truncate(self, text: str) -> str:
        limit = self.settings.max_tool_output
        return text if len(text) <= limit else text[:limit] + "\n...[工具输出已截断]"

    def _list_directory(self, path: str = ".") -> str:
        return list_directory(self.workspace, path)

    def _read_file(self, path: str, start_line: int = 1, line_count: int = 200) -> str:
        return read_file(self.workspace, path, start_line, line_count)

    def _glob_files(self, pattern: str, path: str = ".", max_results: int = 100) -> str:
        return glob_files(self.workspace, pattern, path, max_results)

    def _grep_search(
        self,
        pattern: str,
        path: str = ".",
        file_pattern: str = "*",
        max_results: int = 80,
    ) -> str:
        return grep_search(
            self.workspace, pattern, path, file_pattern, max_results
        )

    def _repo_map(
        self,
        path: str = ".",
        max_files: int = 80,
        max_symbols_per_file: int = 12,
    ) -> str:
        return repo_map(
            self.workspace, path, max_files, max_symbols_per_file
        )

    def _write_file(self, path: str, content: str) -> str:
        return write_file(self.workspace, path, content)

    def _replace_in_file(self, path: str, old_text: str, new_text: str) -> str:
        return replace_in_file(self.workspace, path, old_text, new_text)

    def _apply_patch(
        self,
        path: str,
        start_line: int,
        end_line: int,
        replacement: str,
        expected_text: str | None = None,
    ) -> str:
        return apply_patch(
            self.workspace,
            path,
            start_line,
            end_line,
            replacement,
            expected_text,
        )

    def _run_command(self, command: str) -> str:
        return run_command(
            self.workspace,
            command,
            timeout=self.settings.command_timeout,
            policy=self.command_policy,
        )
