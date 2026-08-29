"""Tool Calling Schema 聚合。"""

from .command_schemas import COMMAND_SCHEMAS
from .file_schemas import FILE_SCHEMAS
from .search_schemas import SEARCH_SCHEMAS

TOOL_SCHEMAS = SEARCH_SCHEMAS + FILE_SCHEMAS + COMMAND_SCHEMAS
TOOL_SCHEMA_BY_NAME = {
    item["function"]["name"]: item
    for item in TOOL_SCHEMAS
}

__all__ = ["TOOL_SCHEMAS", "TOOL_SCHEMA_BY_NAME"]
