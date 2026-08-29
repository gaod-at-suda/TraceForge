"""供 TraceForge 演示使用的简单计算器项目。

可以让 Agent 在这个文件中新增函数、修复 bug 或补充异常处理。
"""


def add(a, b):
    """返回两数之和。"""
    return a + b


def subtract(a, b):
    """返回两数之差。"""
    return a - b


def multiply(a, b):
    """返回两数之积。"""
    return a * b


def divide(a, b):
    """返回两数之商。"""
    if b == 0:
        raise ValueError("除数不能为 0")
    return a / b
