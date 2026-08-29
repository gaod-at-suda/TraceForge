"""税费计算模块。"""


def calculate_tax(amount: float, tax_rate: float) -> float:
    """计算指定金额对应的税费。"""
    if amount < 0:
        raise ValueError("amount 不能为负数")

    if not 0 <= tax_rate <= 1:
        raise ValueError("tax_rate 必须位于 0 到 1 之间")

    return round(amount * tax_rate, 2)
