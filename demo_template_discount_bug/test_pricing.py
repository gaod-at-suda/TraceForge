"""pricing.py 的回归测试。

Debug 场景要求 Agent 修复实现，而不是修改这些测试。
"""

import pytest

from pricing import calculate_price


def test_no_discount_keeps_original_price():
    assert calculate_price(100, 0) == 100


def test_twenty_percent_discount():
    assert calculate_price(100, 0.2) == 80


def test_full_discount_is_free():
    assert calculate_price(59.9, 1) == 0


def test_invalid_discount_above_one():
    with pytest.raises(ValueError):
        calculate_price(100, 1.1)


def test_invalid_discount_below_zero():
    with pytest.raises(ValueError):
        calculate_price(100, -0.1)


def test_negative_price_is_rejected():
    with pytest.raises(ValueError):
        calculate_price(-1, 0.2)
