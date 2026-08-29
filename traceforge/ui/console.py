"""命令行交互界面。"""

from __future__ import annotations


class ConsoleUI:
    """负责用户输入和最终结果显示。"""

    def welcome(self, workspace: str) -> None:
        print("=" * 60)
        print("TraceForge - Lightweight Coding Agent")
        print(f"Workspace: {workspace}")
        print("输入 exit 或 quit 退出。")
        print("=" * 60)

    def read_task(self) -> str:
        return input("\nTraceForge > ").strip()

    def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    def error(self, message: str) -> None:
        print(f"[ERROR] {message}")

    def final(self, message: str) -> None:
        print("\n[FINAL]")
        print(message)
