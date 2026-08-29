"""TraceForge 本地 ``.env`` 配置加载器。

只使用 Python 标准库，避免为了读取本地配置额外引入依赖。
系统/终端中已经存在的环境变量具有更高优先级，不会被 ``.env`` 覆盖。
"""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_env_file(path: str | Path | None = None) -> Path | None:
    """加载本地 ``.env`` 文件，并返回实际加载的路径。

    优先级：已有系统环境变量 > ``.env`` > 程序默认值。
    空行、注释行以及没有 ``=`` 的行会被忽略；值可选单/双引号。
    如果文件不存在则静默返回 ``None``。
    """

    env_path = Path(path) if path is not None else PROJECT_ROOT / ".env"
    env_path = env_path.expanduser().resolve()

    if not env_path.is_file():
        return None

    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]

        os.environ.setdefault(key, value)

    return env_path
