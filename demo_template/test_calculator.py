"""calculator.py 的基础测试。

后续可以让 TraceForge 自主增加更多测试，例如矩阵乘法测试。
"""

from calculator import add, divide, multiply, subtract


def test_add():
    assert add(1, 2) == 3


def test_subtract():
    assert subtract(5, 3) == 2


def test_multiply():
    assert multiply(4, 3) == 12


def test_divide():
    assert divide(8, 2) == 4
