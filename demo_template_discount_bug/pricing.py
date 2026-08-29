"""折扣价格计算示例。

这个小项目故意保留一个实现 Bug，用来测试 TraceForge 是否能够：
运行失败测试 -> 阅读代码 -> 定位根因 -> 修改实现 -> 再次验证。
"""


def calculate_price(price: float, discount: float) -> float:
    """根据折扣比例返回最终价格。

    discount 的取值范围为 0 到 1：
    - 0 表示不打折
    - 0.2 表示减免 20%
    - 1 表示免费
    """
    if price < 0:
        raise ValueError("price 不能为负数")
    if not 0 <= discount <= 1:
        raise ValueError("discount 必须位于 0 到 1 之间")

    # 演示场景故意保留的缺陷：此处返回了折扣金额，而非折后价格，供 Agent 根据失败测试定位并修复。
    return round(price * discount, 2)
