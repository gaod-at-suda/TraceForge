"""轻量级符号提取。

Python 使用 ast 获取准确类/函数；其它常见语言使用保守正则，
目标是生成导航用 Repo Map，而不是替代完整语言服务器。
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Symbol:
    """Repo Map 中展示的一个代码符号。"""

    kind: str
    name: str
    line: int


def extract_symbols(path: Path, text: str) -> list[Symbol]:
    """根据文件类型提取类、函数等高价值符号。"""
    if path.suffix.lower() == ".py":
        return _python_symbols(text)
    return _regex_symbols(text)


def _python_symbols(text: str) -> list[Symbol]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    symbols: list[Symbol] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(Symbol("function", node.name, node.lineno))
        elif isinstance(node, ast.ClassDef):
            symbols.append(Symbol("class", node.name, node.lineno))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(
                        Symbol("method", f"{node.name}.{child.name}", child.lineno)
                    )
    return symbols


_PATTERNS = [
    ("class", re.compile(r"^\s*(?:public\s+)?class\s+([A-Za-z_]\w*)")),
    ("function", re.compile(
        r"^\s*(?:def|function|func|fn)\s+([A-Za-z_]\w*)\s*\("
    )),
    ("function", re.compile(
        r"^\s*(?:public|private|protected|static|virtual|inline|\w+\s+)*"
        r"[\w:<>,\[\]*&]+\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{?"
    )),
]


def _regex_symbols(text: str) -> list[Symbol]:
    symbols: list[Symbol] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in _PATTERNS:
            match = pattern.search(line)
            if match:
                symbols.append(Symbol(kind, match.group(1), line_no))
                break
    return symbols
