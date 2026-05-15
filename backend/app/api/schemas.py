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

class RAGCandidate(BaseModel):
    index: int
    source: str
    preview: str


class RAGRerankRow(BaseModel):
    rank: int
    score: float
    original_index: int
    source: str
    preview: str


class RAGTimings(BaseModel):
    retrieve_ms: float
    rerank_ms: float
    llm_ms: float
    total_ms: float


class RAGResponse(BaseModel):
    """``POST /rag_search`` 响应体。"""
    question: str
    answer: str
    query_rewrite: str = ""
    candidate_count: int = 0
    candidates: list[RAGCandidate] = []
    rerank_rows: list[RAGRerankRow] = []
    timings: RAGTimings = RAGTimings(retrieve_ms=0, rerank_ms=0, llm_ms=0, total_ms=0)


"""====================知识库请求体====================="""


class CreateKnowledgeBaseRequest(BaseModel):
    """创建知识库请求"""
    name: str
    description: str = ""


class UpdateKnowledgeBaseRequest(BaseModel):
    """更新知识库请求"""
    id: int
    name: str
    description: str = ""


class DeleteKnowledgeBaseRequest(BaseModel):
    """删除知识库请求"""
    id: int


class GetKnowledgeBaseRequest(BaseModel):
    """查询知识库请求"""
    id: int


"""====================知识库文档请求体====================="""


class UploadKnowledgeBaseDocumentRequest(BaseModel):
    """上传文档请求"""
    knowledge_base_id: int
    name: str
    file_path: str
    document: str  # document content


class DeleteKnowledgeBaseDocumentRequest(BaseModel):
    """删除文档请求"""
    knowledge_base_id: int
    document_id: int


class GetKnowledgeBaseDocumentRequest(BaseModel):
    """查询文档请求"""
    knowledge_base_id: int
    document_id: int


"""====================知识库响应体====================="""


class KnowledgeBaseResponse(BaseModel):
    """知识库操作响应"""
    answer: dict | list | str


class KnowledgeBaseDocumentResponse(BaseModel):
    """知识库文档操作响应"""
    answer: dict | list | str

"""====================Agent-对话请求体====================="""


class AgentChatRequest(BaseModel):
    """Agent-对话请求"""
    query: str
    mode: str = "agentic"


class AgentChatResponse(BaseModel):
    """Agent-对话响应"""
    answer: str


class AgentStreamRequest(BaseModel):
    """Agent-SSE 流式监控请求"""
    query: str
    session_id: str | None = None
    user_id: str = ""