"""折扣计算模块。"""


def apply_discount(amount: float, discount_rate: float) -> float:
    """根据折扣比例返回折后金额。"""
    if amount < 0:
        raise ValueError("amount 不能为负数")

    if not 0 <= discount_rate <= 1:
        raise ValueError("discount_rate 必须位于 0 到 1 之间")

    return round(amount * (1 - discount_rate), 2)
