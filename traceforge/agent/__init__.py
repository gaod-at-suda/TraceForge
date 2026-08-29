"""Agent 核心模块。

刻意不在包初始化阶段导入 LLMClient 等重依赖，
这样 Context、Session 等纯本地模块可以独立测试。
"""
