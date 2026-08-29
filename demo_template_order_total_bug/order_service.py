"""订单金额计算服务。"""

from discount import apply_discount
from tax import calculate_tax


def calculate_order_total(
    subtotal: float,
    discount_rate: float,
    tax_rate: float,
) -> float:
    """计算折扣和税费后的订单最终金额。"""
    discounted = apply_discount(subtotal, discount_rate)
    tax = calculate_tax(subtotal, tax_rate)
    return round(discounted + tax, 2)
