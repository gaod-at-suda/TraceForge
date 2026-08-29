# TraceForge

**TraceForge — An Observable Autonomous Coding Agent**

> Observe every step. Forge correct code.

TraceForge 是一个自行实现的轻量级本地 Coding Agent Runtime。
它以“代码库理解 → 规划/决策 → 工具执行 → 代码修改 → 自动验证 → 失败修复”
为核心闭环，并通过 EventBus、Trace、Diff 和 HTML 报告让 Agent 的每一步都可观察、可解释。

TraceForge V1 是一个自行实现的轻量级本地 Coding Agent Runtime。
默认入口仍然是“一键直接测试”：在 PyCharm 中运行 `main.py`，
无需在运行时输入自然语言指令。

## V3 新增能力

### 1. Codebase Intelligence

新增三个只读工具：

- `glob_files`：按 glob 查找文件；
- `grep_search`：正则搜索代码并返回行号；
- `repo_map`：提取代码文件中的类、函数、方法，生成精简仓库地图。

这样 Agent 不再只能依赖 `list_directory + read_file` 逐文件盲读。

### 2. Structured Apply Patch

新增 `apply_patch`：

- 明确指定行区间；
- 可用 `expected_text` 校验当前文件是否还是模型刚刚读取的版本；
- 校验失败时拒绝误改并要求重新读取。

原有 `replace_in_file` 继续保留，适合唯一文本精确替换。

### 3. Plan / Auto / Confirm

通过环境变量：

```text
TRACEFORGE_AGENT_MODE=auto
```

支持：

- `plan`：只提供只读工具；
- `auto`：允许 Agent 自主完成任务；
- `confirm`：写操作会被宿主权限层拦截，预留给 Web 审批 UI。

默认自动测试使用 `auto`。

### 4. Context Condenser

Session 仍保存完整历史，但发送给 LLM 的上下文不再只是简单截断：

- 最近若干轮保留原文；
- 较旧历史被确定性压缩；
- 大段旧源码和日志不会无限挤占模型上下文；
- 不额外调用另一个 LLM 做摘要。

### 5. Git Checkpoint / Rollback

当 workspace：

1. 已经是 Git 仓库；
2. 任务开始前工作区完全干净；

TraceForge 会记录当前 HEAD 作为安全 Checkpoint。

如果任务开始前已有用户未提交修改，则自动禁用回滚，
避免 Agent 的恢复逻辑覆盖用户工作。

`demo_project` 每次一键测试都会自动创建干净 Git baseline，
因此可以稳定演示 Checkpoint。

### 6. Automatic Verification

当本轮 Agent 真正修改了文件，并准备结束任务时，
宿主 runtime 会自动检测项目并执行测试。

当前支持检测：

- Python pytest
- Maven
- Gradle Wrapper
- Node npm test
- CMake ctest

如果验证失败，真实错误会重新反馈给 LLM，
让 Agent 继续修复，而不是仅相信模型自己说“测试通过”。

### 7. Event / Trace / HTML Report

继续保留 V2 的：

- EventBus
- JSONL Trace
- 文件 Diff
- HTML 测试报告
- Web Console 基础

并新增 `verification_started / verification_finished`
以及 Checkpoint 信息。

---

## 一键运行

首次安装：

```text
pip install -r requirements.txt
```

在 PyCharm 的 Run Configuration 中配置：

```text
TRACEFORGE_API_KEY=你的API_KEY
TRACEFORGE_MODEL=你的模型名
```

OpenAI-compatible 服务再设置：

```text
TRACEFORGE_BASE_URL=你的Base URL
```

以后直接运行：

```text
main.py
```

程序自动：

1. 运行 TraceForge 自身测试；
2. 重置 demo_project；
3. 创建干净 Git baseline；
4. 跑 demo 基线测试；
5. 执行预设 Coding Agent 任务；
6. Agent 自主搜索、阅读、修改、运行命令；
7. Agent 准备结束时，runtime 自动做独立验证；
8. 最后再执行一次外部 pytest 验收；
9. 生成代码 Diff 和 HTML 报告。

## 更换自动测试任务

修改：

```text
traceforge/demo/config.py
```

中的：

```python
ACTIVE_SCENARIO = "power_function"
```

无需命令行输入。

## 设计原则

TraceForge V1 刻意不加入 LangChain、AutoGen、MCP、Subagent 等重型机制。
核心目标是：用尽量少、清晰、可解释的代码，实现一个完整可靠的
Coding Agent 执行闭环。
