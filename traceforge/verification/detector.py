"""根据项目文件自动判断最合适的验证命令。"""

from __future__ import annotations

from dataclasses import dataclass

from traceforge.workspace.workspace import Workspace


@dataclass(frozen=True)
class VerificationPlan:
    """描述一次自动验证计划。"""

    detected: bool
    command: list[str]
    reason: str


def detect_verification(workspace: Workspace) -> VerificationPlan:
    """优先检测 Python，其次 Java/Gradle/Maven、Node 和 CMake。"""
    root = workspace.root

    if (
        (root / "pytest.ini").exists()
        or (root / "pyproject.toml").exists()
        or any(root.rglob("test_*.py"))
    ):
        import sys
        return VerificationPlan(
            True,
            [sys.executable, "-m", "pytest", "-q"],
            "检测到 Python pytest 测试",
        )

    if (root / "pom.xml").exists():
        return VerificationPlan(True, ["mvn", "test", "-q"], "检测到 Maven 项目")

    if (root / "gradlew").exists():
        return VerificationPlan(True, ["./gradlew", "test"], "检测到 Gradle Wrapper")

    if (root / "package.json").exists():
        return VerificationPlan(True, ["npm", "test", "--", "--runInBand"], "检测到 Node 项目")

    if (root / "CMakeLists.txt").exists():
        return VerificationPlan(
            True,
            ["ctest", "--test-dir", "build", "--output-on-failure"],
            "检测到 CMake 项目",
        )

    return VerificationPlan(False, [], "未检测到可自动执行的测试入口")
