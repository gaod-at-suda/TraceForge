"""命令执行工具 Schema。"""

RUN_COMMAND_SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": "在 workspace 根目录执行命令，受宿主安全策略和超时保护。",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string"}
            },
            "required": ["command"],
        },
    },
}

COMMAND_SCHEMAS = [RUN_COMMAND_SCHEMA]
