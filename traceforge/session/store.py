"""JSONL 会话持久化。

每条消息单独写一行，便于追加、查看和恢复；不会把 API Key 等凭据写入文件。
"""

from __future__ import annotations

import json
from pathlib import Path


class SessionStore:
    """负责把标准 chat message 持久化到 JSONL。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict]:
        """加载历史消息；文件不存在时返回空列表。"""
        if not self.path.exists():
            return []

        messages: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                # 单行损坏时忽略该行，尽量保留其它可恢复历史。
                continue
            if isinstance(item, dict) and "role" in item:
                messages.append(item)
        return messages

    def append(self, message: dict) -> None:
        """追加一条消息。"""
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message, ensure_ascii=False) + "\n")

    def rewrite(self, messages: list[dict]) -> None:
        """重置或修复会话时整体重写。"""
        text = "".join(
            json.dumps(message, ensure_ascii=False) + "\n"
            for message in messages
        )
        self.path.write_text(text, encoding="utf-8")
