"""轻量上下文预算估算。

不绑定特定 tokenizer，使用序列化字符数作为稳定且低成本的近似指标。
"""

from __future__ import annotations

import json


def estimate_chars(messages: list[dict]) -> int:
    """估算消息序列化后的字符数。"""
    return sum(
        len(json.dumps(message, ensure_ascii=False, default=str))
        for message in messages
    )
