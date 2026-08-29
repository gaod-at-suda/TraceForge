"""TraceForge 一键自动测试执行器。

该执行器不读取 input()，整个测试流程由代码中的场景配置驱动。
"""

from __future__ import annotations

import os
import webbrowser
from pathlib import Path

from traceforge.bootstrap import build_runtime
from traceforge.git import GitCheckpointManager
from traceforge.workspace.workspace import Workspace

from .config import (
    ACTIVE_SCENARIO,
    AUTO_OPEN_HTML_REPORT,
    RUN_BASELINE_TESTS,
    RUN_FRAMEWORK_TESTS,
    SCENARIOS,
    VERIFY_AFTER_AGENT,
)
from .git_setup import initialize_demo_git
from .html_report import build_html_report
from .snapshot import compare_snapshots, snapshot_text_files
from .subprocess_test import PytestResult, run_pytest
from .workspace_reset import reset_workspace


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_WORKSPACE = PROJECT_ROOT / "demo_project"
REPORT_DIR = PROJECT_ROOT / ".traceforge_runtime" / "reports"


def _print_title(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def _show_pytest_result(label: str, result: PytestResult) -> None:
    status = "PASS" if result.success else "FAIL"
    print(f"[{status}] {label}")
    print(result.output)


def _show_baseline_result(result: PytestResult, should_pass: bool) -> bool:
    """检查场景的初始 pytest 状态是否符合预期。"""
    matches_expectation = result.success == should_pass

    if should_pass:
        label = "PASS" if result.success else "UNEXPECTED FAIL"
    else:
        label = "UNEXPECTED PASS" if result.success else "EXPECTED FAIL"

    print(f"[{label}] baseline pytest")
    print(result.output)

    if matches_expectation:
        if should_pass:
            print("[PASS] 原始工程测试通过，baseline 状态符合场景预期。")
        else:
            print("[PASS] 已确认原始工程存在可复现 Bug，开始 Agent Debug。")
    else:
        expected = "通过" if should_pass else "失败"
        actual = "通过" if result.success else "失败"
        print(f"[FAIL] baseline 状态异常：预期 {expected}，实际 {actual}。")

    return matches_expectation


def _run_framework_tests() -> bool:
    """运行 TraceForge 自身 tests/，验证框架底层模块没有回归。"""
    _print_title("1. TraceForge 框架单元测试")
    result = run_pytest(PROJECT_ROOT, ["tests"])
    _show_pytest_result("framework tests", result)
    return result.success


def _check_api_key() -> bool:
    """真实 Agent 集成测试仍需要通过环境变量提供模型 API Key。"""
    if os.getenv("TRACEFORGE_API_KEY", "").strip():
        return True

    _print_title("缺少模型 API Key")
    print(
        "本地单元测试可以直接运行，但真实 Agent 任务需要 TRACEFORGE_API_KEY。\n"
        "请复制项目根目录 .env.example 为 .env，或通过系统环境变量配置：\n"
        "TRACEFORGE_API_KEY=你的Key\n"
        "TRACEFORGE_MODEL=你的模型名\n"
        "如使用 OpenAI-compatible 服务，再配置 TRACEFORGE_BASE_URL。\n"
        "配置完成后重新运行 python main.py。"
    )
    return False


def _protected_files_unchanged(
    protected_files: tuple[str, ...],
    before: dict[str, str],
    after: dict[str, str],
) -> bool:
    """确认 Debug 场景中不允许模型修改的文件保持原样。"""
    if not protected_files:
        return True

    changed = [
        path
        for path in protected_files
        if before.get(path) != after.get(path)
    ]

    if changed:
        print(
            "[FAIL] Agent 修改了受保护文件："
            + ", ".join(changed)
            + "。该 Debug 场景要求通过修复实现解决问题，不能改测试绕过失败。"
        )
        return False

    print(
        "[PASS] 受保护文件保持不变："
        + ", ".join(protected_files)
    )
    return True


def _exercise_rollback(
    runtime,
    run_id: str,
    checkpoint,
    before: dict[str, str],
) -> tuple[bool, str]:
    """模拟最终验收失败并验证源码、Git 状态与测试都恢复到 baseline。"""
    _print_title("7. 模拟最终验收失败并测试 Rollback")
    reason = "Demo 注入的最终验收失败，用于端到端验证 Git Rollback"
    print(f"[EXPECTED FAIL] {reason}")
    runtime.event_bus.emit(
        "acceptance_failed",
        run_id,
        data={"reason": reason, "simulated": True},
    )

    runtime.event_bus.emit(
        "rollback_started",
        run_id,
        data={
            "revision": checkpoint.revision,
            "reason": reason,
        },
    )
    rollback_ok = runtime.checkpoint_manager.rollback(checkpoint)
    runtime.event_bus.emit(
        "rollback_finished",
        run_id,
        data={
            "success": rollback_ok,
            "revision": checkpoint.revision,
        },
    )

    restored = snapshot_text_files(DEMO_WORKSPACE)
    snapshot_ok = restored == before

    # create() 仅在 Git 工作区干净时启用，因此该结果同时用于确认基线状态可安全回滚。
    clean_probe = runtime.checkpoint_manager.create()
    git_clean = clean_probe.enabled

    post_rollback = run_pytest(DEMO_WORKSPACE)

    print(f"[{'PASS' if rollback_ok else 'FAIL'}] git reset/clean 执行结果")
    print(f"[{'PASS' if snapshot_ok else 'FAIL'}] Rollback 后文本快照与 baseline 一致")
    print(f"[{'PASS' if git_clean else 'FAIL'}] Rollback 后 Git 工作区干净")
    _show_pytest_result("post-rollback baseline pytest", post_rollback)

    success = rollback_ok and snapshot_ok and git_clean and post_rollback.success
    if success:
        print("[PASS] Rollback 端到端验收通过：源码、Git 状态和 baseline 测试均已恢复。")
    else:
        print("[FAIL] Rollback 端到端验收未完全通过。")

    details = (
        "模拟最终验收失败后执行 Git Rollback\n"
        f"rollback_command_success={rollback_ok}\n"
        f"snapshot_restored={snapshot_ok}\n"
        f"git_clean={git_clean}\n"
        f"post_rollback_pytest_success={post_rollback.success}\n"
        f"post_rollback_pytest_output:\n{post_rollback.output}"
    )
    return success, details


def run_direct_test() -> int:
    """执行从重置工作区到最终验收的完整测试。"""
    scenario = SCENARIOS[ACTIVE_SCENARIO]
    demo_template = PROJECT_ROOT / scenario.template_dir

    _print_title("TraceForge Direct Test")
    print(f"测试场景：{scenario.name}")
    print(f"场景说明：{scenario.description}")
    print(f"模板：{demo_template}")
    print(f"工作区：{DEMO_WORKSPACE}")
    print("\n预设任务：")
    print(scenario.task)

    if not demo_template.is_dir():
        print(f"\n[FAIL] Demo 模板目录不存在：{demo_template}")
        return 1

    if RUN_FRAMEWORK_TESTS and not _run_framework_tests():
        print("\nTraceForge 自身单元测试失败，停止真实 Agent 测试。")
        return 1

    _print_title("2. 重置 Demo Workspace")
    reset_workspace(demo_template, DEMO_WORKSPACE)
    print(f"[PASS] 已从 {demo_template.name} 重建 {DEMO_WORKSPACE.name}")
    initialize_demo_git(DEMO_WORKSPACE)
    print("[PASS] 已创建干净 Git baseline，可测试 Checkpoint/Rollback")

    if RUN_BASELINE_TESTS:
        _print_title("3. Demo 基线 pytest")
        baseline = run_pytest(DEMO_WORKSPACE)
        if not _show_baseline_result(baseline, scenario.baseline_should_pass):
            print("\nDemo baseline 与场景定义不一致，停止真实 Agent 测试。")
            return 1

    checkpoint_probe = GitCheckpointManager(Workspace(DEMO_WORKSPACE)).create()
    if not checkpoint_probe.enabled:
        print(f"\n[FAIL] Git Checkpoint 不可用：{checkpoint_probe.reason}")
        return 1

    revision = checkpoint_probe.revision[:12]
    print(
        f"[PASS] Git Checkpoint 已就绪：{revision} "
        f"({checkpoint_probe.reason})"
    )

    before = snapshot_text_files(DEMO_WORKSPACE)

    if not _check_api_key():
        return 1

    _print_title("4. 自动执行真实 Coding Agent 任务")
    runtime = build_runtime(str(DEMO_WORKSPACE), enable_console_log=True)
    runtime.agent.reset_session()
    runtime.event_store.clear()

    result = runtime.agent.run(scenario.task)

    print("\n[AGENT FINAL]")
    print(result.message)
    print(f"\nAgent success={result.success}, steps={result.steps}, run_id={result.run_id}")

    after = snapshot_text_files(DEMO_WORKSPACE)
    diffs = compare_snapshots(before, after)

    _print_title("5. 文件修改摘要")
    if not diffs:
        print("Agent 没有修改文本文件。")
    else:
        for path, diff in diffs.items():
            print(f"\n--- {path} ---")
            print(diff)

    protected_files_ok = _protected_files_unchanged(
        scenario.protected_files,
        before,
        after,
    )

    verification = PytestResult(
        success=True,
        return_code=0,
        output="已关闭 VERIFY_AFTER_AGENT，未执行最终 pytest。",
    )

    if VERIFY_AFTER_AGENT:
        _print_title("6. 独立 pytest 最终验收")
        verification = run_pytest(DEMO_WORKSPACE)
        _show_pytest_result("final verification", verification)

    rollback_ok = True
    rollback_details = ""
    if scenario.exercise_rollback:
        # 仅在 Agent 执行和独立验证均成功后注入受控失败，
        # 以确定性验证 Rollback，而不依赖模型产生随机错误。
        if result.success and verification.success and bool(diffs):
            rollback_ok, rollback_details = _exercise_rollback(
                runtime,
                result.run_id,
                checkpoint_probe,
                before,
            )
        else:
            rollback_ok = False
            rollback_details = (
                "未进入 Rollback 阶段：要求 Agent success、最终 pytest PASS 且确实产生文件修改。"
            )
            print(f"\n[FAIL] {rollback_details}")

    events = runtime.event_store.after(0)
    report_path = REPORT_DIR / f"{result.run_id or 'unknown'}_report.html"

    verification_output = verification.output
    if scenario.exercise_rollback:
        verification_output += "\n\n=== Rollback E2E ===\n" + rollback_details

    report_success = (
        result.success
        and verification.success
        and protected_files_ok
        and rollback_ok
    )

    build_html_report(
        output_path=report_path,
        scenario_name=scenario.name,
        scenario_description=scenario.description,
        task=scenario.task,
        agent_success=result.success and protected_files_ok,
        agent_message=result.message,
        agent_steps=result.steps,
        verification_success=verification.success and protected_files_ok and rollback_ok,
        verification_output=verification_output,
        events=events,
        diffs=diffs,
    )

    _print_title("8. 测试报告" if scenario.exercise_rollback else "7. 测试报告")
    print(f"HTML 报告：{report_path}")

    if AUTO_OPEN_HTML_REPORT:
        try:
            webbrowser.open(report_path.resolve().as_uri())
            print("[INFO] 已尝试使用默认浏览器打开报告。")
        except Exception as exc:
            print(f"[WARN] 自动打开浏览器失败：{exc}")

    print(
        "\n"
        + (
            "[PASS] 一键 Agent 测试通过。"
            if report_success
            else "[FAIL] 一键 Agent 测试未完全通过。"
        )
    )
    return 0 if report_success else 1
