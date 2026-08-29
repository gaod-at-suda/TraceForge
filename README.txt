TraceForge — An Observable Autonomous Coding Agent

Git 仓库地址：
<请替换为最终 Git 仓库地址>

一、项目简介
TraceForge 是一个从零实现的轻量级 Coding Agent。用户可在 Web 页面中选择本地工作区并输入自然语言任务，Agent 会自主分析代码、调用工具、修改文件、运行测试，并展示执行时间线、代码 Diff 与验证结果。项目未使用 LangChain、AutoGen、OpenAI Agents SDK 等 Agent 框架，Agent Loop、上下文管理、工具调度、终止策略、错误恢复与回滚均自行实现。

二、运行方式
1. 安装依赖：pip install -r requirements.txt
2. 复制 .env.example 为 .env，填写 TRACEFORGE_API_KEY、模型名和 BASE_URL。
3. 启动 Web UI：python web_main.py
   浏览器访问 http://127.0.0.1:8765
4. 一键运行内置场景：python main.py
5. 运行单元测试：pytest -q

三、特色功能
1. 自主 Agent Loop：支持多轮 Tool Calling、最大步数控制和最终收尾。
2. 代码库理解：提供 repo_map、glob_files、grep_search、分页 read_file。
3. 安全工具执行：支持 write_file、replace_in_file、apply_patch、run_command，并限制工作区越界和危险命令。
4. 自动验证：修改后自动检测并执行 pytest 等测试，失败信息可反馈给模型继续修复。
5. Git Checkpoint / Rollback：任务开始前记录干净基线，失败时自动恢复源码和工作区。
6. 可观测性：记录 Timeline、Tool Call、错误、文件 Diff、验证结果，并生成 HTML 报告。
7. Web UI：支持自行选择 Workspace、输入任意编程任务并实时观察 Agent 工作过程。

四、说明
API Key 仅通过环境变量或本地 .env 加载；.env 已加入 .gitignore，请勿提交真实密钥或在演示视频中展示。
