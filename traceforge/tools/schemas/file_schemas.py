"""文件读取与编辑工具 Schema。"""

READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "按行分页读取文本文件，返回带行号内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "line_count": {"type": "integer", "minimum": 1, "maximum": 400},
            },
            "required": ["path"],
        },
    },
}

WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "创建或完整覆盖文本文件；仅适合新文件或小文件。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
}

REPLACE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "replace_in_file",
        "description": "把唯一出现的旧文本精确替换为新文本。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
}

APPLY_PATCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "apply_patch",
        "description": (
            "按明确行区间执行结构化 Patch。复杂局部编辑优先使用它；"
            "修改前先 read_file 获取最新行号。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 0},
                "replacement": {"type": "string"},
                "expected_text": {
                    "type": "string",
                    "description": "可选：目标区间当前文本，用于避免基于过期内容修改",
                },
            },
            "required": ["path", "start_line", "end_line", "replacement"],
        },
    },
}

FILE_SCHEMAS = [
    READ_FILE_SCHEMA,
    WRITE_FILE_SCHEMA,
    REPLACE_SCHEMA,
    APPLY_PATCH_SCHEMA,
]
