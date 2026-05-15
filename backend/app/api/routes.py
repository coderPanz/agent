import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.api.schemas import (
    HealthResponse,
    RAGResponse,
    RAGRequest,
    RAGCandidate,
    RAGRerankRow,
    RAGTimings,
    KnowledgeBaseResponse,
    KnowledgeBaseDocumentResponse,
    CreateKnowledgeBaseRequest,
    UpdateKnowledgeBaseRequest,
    DeleteKnowledgeBaseRequest,
    GetKnowledgeBaseRequest,
    UploadKnowledgeBaseDocumentRequest,
    DeleteKnowledgeBaseDocumentRequest,
    GetKnowledgeBaseDocumentRequest,
    AgentChatRequest,
    AgentChatResponse,
    AgentStreamRequest,
)
from app.services.rag import (
    rag_search as rag_search_service,
    rag_search_debug as rag_search_debug_service,
    create_knowledge_base_service,
    delete_knowledge_base_service,
    update_knowledge_base_service,
    get_knowledge_base_service,
    list_knowledge_bases_service,
    upload_knowledge_base_document_service,
    delete_knowledge_base_document_service,
    get_knowledge_base_document_service,
    list_knowledge_base_documents_service,
)
from app.core.agent.agent_runtime import AgentRuntime

_runtime = AgentRuntime()

router = APIRouter()

"""====================存活探针====================="""
@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse()

"""====================RAG 搜索====================="""
@router.post("/rag_search", response_model=RAGResponse, tags=["rag"])
def rag_search(request: RAGRequest) -> RAGResponse:
    result = rag_search_debug_service(request.query, request.mode)
    return RAGResponse(
        question=result["question"],
        answer=result["answer"],
        query_rewrite=result.get("query_rewrite", ""),
        candidate_count=result["candidate_count"],
        candidates=[RAGCandidate(**c) for c in result["candidates"]],
        rerank_rows=[RAGRerankRow(**r) for r in result["rerank_rows"]],
        timings=RAGTimings(**result["timings"]),
    )

@router.post("/rag_search_debug", tags=["rag"])
def rag_search_debug(request: RAGRequest) -> dict:
    return rag_search_debug_service(request.query, request.mode)

"""====================RAG 知识库创建====================="""
@router.post("/create_knowledge_base", response_model=KnowledgeBaseResponse, tags=["rag"])
def create_knowledge_base(request: CreateKnowledgeBaseRequest) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse(answer=create_knowledge_base_service(request.name, request.description))

"""====================RAG 知识库删除====================="""
@router.delete("/delete_knowledge_base", response_model=KnowledgeBaseResponse, tags=["rag"])
def delete_knowledge_base(request: DeleteKnowledgeBaseRequest) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse(answer=delete_knowledge_base_service(request.id))

"""====================RAG 知识库更新====================="""
@router.put("/update_knowledge_base", response_model=KnowledgeBaseResponse, tags=["rag"])
def update_knowledge_base(request: UpdateKnowledgeBaseRequest) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse(answer=update_knowledge_base_service(request.id, request.name, request.description))

"""====================RAG 知识库查询====================="""
@router.get("/get_knowledge_base", response_model=KnowledgeBaseResponse, tags=["rag"])
def get_knowledge_base(id: int) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse(answer=get_knowledge_base_service(id))

"""====================RAG 知识库列表====================="""
@router.get("/list_knowledge_bases", response_model=KnowledgeBaseResponse, tags=["rag"])
def list_knowledge_bases(skip: int = 0, limit: int = 10) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse(answer=list_knowledge_bases_service(skip, limit))

"""====================RAG 知识库-文档上传====================="""
@router.post("/upload_knowledge_base_document", response_model=KnowledgeBaseDocumentResponse, tags=["rag"])
def upload_knowledge_base_document(request: UploadKnowledgeBaseDocumentRequest) -> KnowledgeBaseDocumentResponse:
    return KnowledgeBaseDocumentResponse(answer=upload_knowledge_base_document_service(
        request.knowledge_base_id,
        request.name,
        request.file_path,
        request.document
    ))

"""====================RAG 知识库-文档删除====================="""
@router.delete("/delete_knowledge_base_document", response_model=KnowledgeBaseDocumentResponse, tags=["rag"])
def delete_knowledge_base_document(request: DeleteKnowledgeBaseDocumentRequest) -> KnowledgeBaseDocumentResponse:
    return KnowledgeBaseDocumentResponse(answer=delete_knowledge_base_document_service(request.knowledge_base_id, request.document_id))

"""====================RAG 知识库-文档查询====================="""
@router.get("/get_knowledge_base_document", response_model=KnowledgeBaseDocumentResponse, tags=["rag"])
def get_knowledge_base_document(knowledge_base_id: int, document_id: int) -> KnowledgeBaseDocumentResponse:
    return KnowledgeBaseDocumentResponse(answer=get_knowledge_base_document_service(knowledge_base_id, document_id))

"""====================RAG 知识库-文档列表====================="""
@router.get("/list_knowledge_base_documents", response_model=KnowledgeBaseDocumentResponse, tags=["rag"])
def list_knowledge_base_documents(knowledge_base_id: int, skip: int = 0, limit: int = 10) -> KnowledgeBaseDocumentResponse:
    return KnowledgeBaseDocumentResponse(answer=list_knowledge_base_documents_service(knowledge_base_id, skip, limit))


"""====================Agent-对话====================="""
@router.post("/agent_chat", response_model=AgentChatResponse, tags=["agent"])
async def agent_chat(request: AgentChatRequest) -> AgentChatResponse:
    answer = await _runtime.chat(request.query, session_id=None)
    return AgentChatResponse(answer=answer)


"""====================Agent-SSE 监控流====================="""
@router.post("/agent/stream", tags=["agent"])
async def agent_stream(request: AgentStreamRequest) -> StreamingResponse:
    """
    SSE 事件流接口，前端通过此接口实时监控 Agent 执行过程。

    事件格式（每行以 "data: " 开头，空行分隔）：
      data: {"type": "start",     "session_id": "..."}
      data: {"type": "node_done", "name": "router", "label": "意图识别", "detail": "chat"}
      data: {"type": "tool_call", "tools": {"web_search": 3}, "total": 3}
      data: {"type": "node_done", "name": "react_executor", "label": "思考推理", "detail": "2 步推理"}
      data: {"type": "answer",    "content": "最终回答..."}
      data: {"type": "done"}
    """
    async def event_generator():
        async for evt in _runtime.stream_events(
            request.query, request.session_id, request.user_id
        ):
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # 禁用 nginx 缓冲，保证实时推送
        },
    )