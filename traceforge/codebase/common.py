"""代码库搜索公共规则。"""

from __future__ import annotations

from pathlib import Path

IGNORED_DIRS = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".traceforge_runtime",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
}

TEXT_EXTENSIONS = {
    ".py", ".java", ".cpp", ".cc", ".c", ".h", ".hpp",
    ".js", ".ts", ".tsx", ".jsx", ".go", ".rs",
    ".md", ".txt", ".json", ".yaml", ".yml", ".toml",
}


def is_ignored(path: Path) -> bool:
    """判断路径是否包含常见缓存、依赖或运行时目录。"""
    return any(part in IGNORED_DIRS for part in path.parts)
