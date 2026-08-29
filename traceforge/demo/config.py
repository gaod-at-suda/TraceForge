"""一键测试场景配置。

想更换测试任务时，直接修改 ACTIVE_SCENARIO 即可，
无需在运行时通过命令行输入指令。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoScenario:
    """描述一个可重复执行的 Coding Agent 测试场景。"""

    name: str
    description: str
    task: str
    template_dir: str = "demo_template"
    baseline_should_pass: bool = True
    protected_files: tuple[str, ...] = ()
    exercise_rollback: bool = False


SCENARIOS = {
    "power_function": DemoScenario(
        name="power_function",
        description="新增幂运算函数、补充单元测试并执行 pytest",
        task=(
            "请检查当前项目，为 calculator.py 新增 power(a, b) 函数，"
            "返回 a 的 b 次幂；然后在 test_calculator.py 中补充至少 3 个相关单元测试，"
            "包含普通正整数指数、0 次幂和负指数。"
            "完成修改后必须运行 pytest -q 验证所有测试通过。"
            "如果测试失败，请根据错误继续修改，直到测试通过后再结束任务。"
        ),
    ),
    "matrix_multiply": DemoScenario(
        name="matrix_multiply",
        description="新增矩阵乘法、异常检查、测试并执行 pytest",
        task=(
            "请检查当前项目，为 calculator.py 新增 matrix_multiply(a, b) 函数，"
            "实现二维矩阵乘法，并在矩阵维度不匹配时抛出 ValueError。"
            "请在 test_calculator.py 中补充正常矩阵乘法和维度不匹配的测试，"
            "最后运行 pytest -q 验证全部测试通过；若失败请继续修复。"
        ),
    ),
    "refactor_divide": DemoScenario(
        name="refactor_divide",
        description="增强除法函数测试覆盖并验证异常行为",
        task=(
            "请检查 calculator.py 中的 divide 函数，保持已有行为兼容，"
            "并为 test_calculator.py 增加更完整的除法测试，包括浮点除法、负数除法"
            "以及除数为 0 时抛出 ValueError。完成后运行 pytest -q 验证。"
        ),
    ),
    "discount_bug": DemoScenario(
        name="discount_bug",
        description="根据失败测试自主定位并修复折扣计算 Bug",
        template_dir="demo_template_discount_bug",
        baseline_should_pass=False,
        protected_files=("test_pricing.py",),
        task=(
            "当前项目存在一个与折扣价格计算有关的 Bug，已有测试能够复现问题。"
            "请先运行 pytest -q 查看失败信息，然后自行检查相关代码、定位根因并修复。"
            "要求：不要删除、跳过、修改或弱化已有测试；保持现有公开函数接口兼容；"
            "修改应尽量小且针对根因。修复后必须重新运行 pytest -q，"
            "只有全部测试通过后才能结束任务。"
        ),
    ),
    "order_total_bug": DemoScenario(
        name="order_total_bug",
        description="跨多个模块定位并修复订单最终金额计算 Bug",
        template_dir="demo_template_order_total_bug",
        baseline_should_pass=False,
        protected_files=("test_order_service.py",),
        task=(
            "当前项目的订单最终金额计算存在 Bug，已有测试能够复现问题。"
            "请先运行 pytest -q 查看失败信息，然后自行分析项目结构、相关模块和调用关系，"
            "定位真正根因并进行最小修复。"
            "要求：不要删除、跳过、修改或弱化已有测试；保持现有公开函数接口兼容；"
            "不要针对测试结果硬编码；修复后必须重新运行 pytest -q，"
            "只有全部测试通过后才能结束任务。"
        ),
    ),
    "rollback_recovery": DemoScenario(
        name="rollback_recovery",
        description="完成真实代码修改后模拟最终验收失败，并验证 Git 自动回滚",
        template_dir="demo_template_rollback",
        baseline_should_pass=True,
        exercise_rollback=True,
        task=(
            "请检查当前项目，为 calculator.py 新增 square(x) 函数，返回 x 的平方；"
            "并在 test_calculator.py 中至少增加正数、负数和 0 的测试。"
            "完成后必须运行 pytest -q，确保全部测试通过后再结束任务。"
        ),
    ),
}

# 默认使用跨模块 Bug 修复场景，完整展示失败测试、代码分析、最小修改与宿主验证流程。
# Rollback 场景仍保留在 SCENARIOS 中，可单独用于验证失败恢复链路。
ACTIVE_SCENARIO = "order_total_bug"

# 是否在 Agent 集成测试前运行 TraceForge 自身的单元测试。
RUN_FRAMEWORK_TESTS = True

# 是否在 Agent 执行前验证 Demo 工作区的初始测试状态。
RUN_BASELINE_TESTS = True

# Agent 结束后是否由宿主程序再次运行 Demo 测试，作为独立于模型结论的最终验收。
VERIFY_AFTER_AGENT = True

# 是否在场景结束后使用系统默认浏览器打开生成的静态 HTML 报告。
AUTO_OPEN_HTML_REPORT = True
