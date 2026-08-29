"""代码库只读搜索工具 Schema。"""

LIST_DIRECTORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_directory",
        "description": "列出工作区指定目录的直接子项。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对工作区路径，默认 ."}
            },
            "required": [],
        },
    },
}

GLOB_SCHEMA = {
    "type": "function",
    "function": {
        "name": "glob_files",
        "description": "使用 glob 模式查找文件，例如 **/*.py。",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "description": "搜索根目录，默认 ."},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 300},
            },
            "required": ["pattern"],
        },
    },
}

GREP_SCHEMA = {
    "type": "function",
    "function": {
        "name": "grep_search",
        "description": "正则搜索代码内容，返回 文件:行号:匹配内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Python 正则表达式"},
                "path": {"type": "string", "description": "搜索根目录，默认 ."},
                "file_pattern": {"type": "string", "description": "文件名 glob，例如 *.py"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 300},
            },
            "required": ["pattern"],
        },
    },
}

REPO_MAP_SCHEMA = {
    "type": "function",
    "function": {
        "name": "repo_map",
        "description": "生成精简项目地图，展示文件和类/函数等关键符号。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_files": {"type": "integer", "minimum": 1, "maximum": 200},
                "max_symbols_per_file": {"type": "integer", "minimum": 1, "maximum": 30},
            },
            "required": [],
        },
    },
}

SEARCH_SCHEMAS = [
    LIST_DIRECTORY_SCHEMA,
    GLOB_SCHEMA,
    GREP_SCHEMA,
    REPO_MAP_SCHEMA,
]
