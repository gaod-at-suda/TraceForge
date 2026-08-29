"""测试工作区重置。

每次一键测试都从 demo_template 复制出全新的 demo_project，
避免上一次 Agent 修改残留影响下一轮结果。
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path


def _retry_remove_readonly(func, path: str, exc_info) -> None:
    """Windows 下清除 Git 只读文件属性后重试删除。

    Git 的 loose object 在 Windows 上可能带只读属性，直接使用
    ``shutil.rmtree`` 会触发 WinError 5。这里只在删除失败时给目标
    补上当前用户写权限并重试；如果失败原因不是 PermissionError，
    则保留原异常，避免吞掉真实问题。

    ``shutil.rmtree`` 在 Python 3.12 的 ``onexc`` 会直接传异常对象，
    旧版本 ``onerror`` 则传 ``sys.exc_info()`` 元组，因此这里兼容两种形式。
    """
    exc = exc_info[1] if isinstance(exc_info, tuple) else exc_info
    if not isinstance(exc, PermissionError):
        raise exc

    try:
        current_mode = os.stat(path).st_mode
        os.chmod(path, current_mode | stat.S_IWUSR)
    except OSError:
        # 让下面的重试给出真正的删除错误。
        pass

    func(path)


def _remove_tree(path: Path) -> None:
    """兼容不同 Python 版本地删除目录树。"""
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_retry_remove_readonly)
    else:
        # Python < 3.12 尚无 onexc；onerror 的第三个参数是 exc_info 元组。
        shutil.rmtree(path, onerror=_retry_remove_readonly)


def reset_workspace(template_dir: Path, workspace_dir: Path) -> None:
    """删除旧测试工作区，并从模板目录重新复制。"""
    if workspace_dir.exists():
        _remove_tree(workspace_dir)

    shutil.copytree(template_dir, workspace_dir)
