"""订单金额计算回归测试。"""

import pytest

from order_service import calculate_order_total


def test_discount_then_tax():
    assert calculate_order_total(100, 0.2, 0.1) == 88


def test_no_discount():
    assert calculate_order_total(100, 0, 0.1) == 110


def test_full_discount():
    assert calculate_order_total(100, 1, 0.1) == 0


def test_no_tax():
    assert calculate_order_total(100, 0.2, 0) == 80


def test_invalid_discount():
    with pytest.raises(ValueError):
        calculate_order_total(100, 1.2, 0.1)


def test_invalid_tax():
    with pytest.raises(ValueError):
        calculate_order_total(100, 0.2, 1.2)


def test_negative_subtotal():
    with pytest.raises(ValueError):
        calculate_order_total(-100, 0.2, 0.1)
