"""响应体schemas 定义"""

from pydantic import BaseModel #  # 数据模型基类、字段增强描述与校验


class HealthResponse(BaseModel):
    """``GET /health`` 存活探针的最小响应。"""
    status: str = "ok"
    version: str = "1.0.0"

class RAGRequest(BaseModel):
    """``POST /rag_search`` 请求体。"""
    query: str
    mode: str = "agentic"

class RAGResponse(BaseModel):
    """``POST /rag_search`` 响应体。"""
    answer: str