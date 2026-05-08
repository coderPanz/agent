from fastapi import APIRouter
from app.api.schemas import HealthResponse, RAGResponse, RAGRequest
from app.services.rag import rag_search as rag_search_service

router = APIRouter()

@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """存活探针：负载均衡或 K8s 常用，用来判断服务是否已起来。"""
    return HealthResponse()


@router.post("/rag_search", response_model=RAGResponse, tags=["rag"])
def rag_search(request: RAGRequest) -> RAGResponse:
    """RAG 处理：用户输入问题，返回答案。"""
    return RAGResponse(answer=rag_search_service(request.query, request.mode))

