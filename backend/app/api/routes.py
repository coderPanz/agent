from fastapi import APIRouter
from app.api.schemas import (
    HealthResponse,
    RAGResponse,
    RAGRequest,
    KnowledgeBaseResponse,
    KnowledgeBaseDocumentResponse,
    CreateKnowledgeBaseRequest,
    UpdateKnowledgeBaseRequest,
    DeleteKnowledgeBaseRequest,
    GetKnowledgeBaseRequest,
    UploadKnowledgeBaseDocumentRequest,
    DeleteKnowledgeBaseDocumentRequest,
    GetKnowledgeBaseDocumentRequest,
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

router = APIRouter()

"""====================存活探针====================="""
@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse()

"""====================RAG 搜索====================="""
@router.post("/rag_search", response_model=RAGResponse, tags=["rag"])
def rag_search(request: RAGRequest) -> RAGResponse:
    return RAGResponse(answer=rag_search_service(request.query, request.mode))

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
