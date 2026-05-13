from pydantic import BaseModel
from typing import Any

class ToolResult(BaseModel):
    """工具执行的标准格式"""
    tool_name: str
    output: str
    success: bool
    error: str | None = None
    raw: Any = None