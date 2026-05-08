"""RAG 服务"""
from sqlalchemy.orm import Session
from app.core.rag.rag_mode.agentic_rag import agentic_rag
from app.core.rag.rag_mode.common_rag import common_rag
from app.services.database import SessionLocal
from app.models.rag.knowledge import KnowledgeBase
from app.models.rag.knowledge_docs import Document


"""====================RAG 搜索====================="""
def rag_search(query: str, mode: str = "agentic") -> str:
    """RAG 搜索"""
    if mode == "agentic":
        return agentic_rag(query)
    elif mode == "common":
        return common_rag(query)
    else:
        raise ValueError(f"Invalid mode: {mode}")


"""====================RAG 知识库 CRUD====================="""


def create_knowledge_base_service(name: str, description: str = "") -> dict:
    """创建知识库"""
    db: Session = SessionLocal()
    try:
        kb = KnowledgeBase(name=name, description=description)
        db.add(kb)
        db.commit()
        db.refresh(kb)
        return {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "created_at": kb.created_at.isoformat() if kb.created_at else None,
        }
    finally:
        db.close()


def delete_knowledge_base_service(kb_id: int) -> dict:
    """删除知识库"""
    db: Session = SessionLocal()
    try:
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise ValueError(f"知识库不存在: {kb_id}")
        db.delete(kb)
        db.commit()
        return {"id": kb_id, "message": "删除成功"}
    finally:
        db.close()


def update_knowledge_base_service(kb_id: int, name: str, description: str = "") -> dict:
    """更新知识库"""
    db: Session = SessionLocal()
    try:
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise ValueError(f"知识库不存在: {kb_id}")
        kb.name = name
        kb.description = description
        db.commit()
        db.refresh(kb)
        return {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "created_at": kb.created_at.isoformat() if kb.created_at else None,
        }
    finally:
        db.close()


def get_knowledge_base_service(kb_id: int) -> dict:
    """查询知识库"""
    db: Session = SessionLocal()
    try:
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise ValueError(f"知识库不存在: {kb_id}")
        return {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "created_at": kb.created_at.isoformat() if kb.created_at else None,
            "documents_count": len(kb.documents),
        }
    finally:
        db.close()


def list_knowledge_bases_service(skip: int = 0, limit: int = 10) -> list:
    """列出所有知识库"""
    db: Session = SessionLocal()
    try:
        kbs = db.query(KnowledgeBase).offset(skip).limit(limit).all()
        return [
            {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "created_at": kb.created_at.isoformat() if kb.created_at else None,
                "documents_count": len(kb.documents),
            }
            for kb in kbs
        ]
    finally:
        db.close()


"""====================RAG 知识库文档 CRUD====================="""


def upload_knowledge_base_document_service(
    kb_id: int, name: str, file_path: str, content: str
) -> dict:
    """上传文档到知识库"""
    db: Session = SessionLocal()
    try:
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise ValueError(f"知识库不存在: {kb_id}")

        doc = Document(
            name=name,
            file_path=file_path,
            content=content,
            knowledge_base_id=kb_id,
            status="pending",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return {
            "id": doc.id,
            "name": doc.name,
            "file_path": doc.file_path,
            "status": doc.status,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
    finally:
        db.close()


def delete_knowledge_base_document_service(kb_id: int, doc_id: int) -> dict:
    """删除知识库中的文档"""
    db: Session = SessionLocal()
    try:
        doc = (
            db.query(Document)
            .filter(Document.id == doc_id, Document.knowledge_base_id == kb_id)
            .first()
        )
        if not doc:
            raise ValueError(f"文档不存在: {doc_id}")
        db.delete(doc)
        db.commit()
        return {"id": doc_id, "message": "删除成功"}
    finally:
        db.close()


def get_knowledge_base_document_service(kb_id: int, doc_id: int) -> dict:
    """查询知识库中的文档"""
    db: Session = SessionLocal()
    try:
        doc = (
            db.query(Document)
            .filter(Document.id == doc_id, Document.knowledge_base_id == kb_id)
            .first()
        )
        if not doc:
            raise ValueError(f"文档不存在: {doc_id}")
        return {
            "id": doc.id,
            "name": doc.name,
            "file_path": doc.file_path,
            "content": doc.content,
            "status": doc.status,
            "knowledge_base_id": doc.knowledge_base_id,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
    finally:
        db.close()


def list_knowledge_base_documents_service(kb_id: int, skip: int = 0, limit: int = 10) -> list:
    """列出知识库中的所有文档"""
    db: Session = SessionLocal()
    try:
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise ValueError(f"知识库不存在: {kb_id}")

        docs = (
            db.query(Document)
            .filter(Document.knowledge_base_id == kb_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": doc.id,
                "name": doc.name,
                "file_path": doc.file_path,
                "status": doc.status,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in docs
        ]
    finally:
        db.close()


def update_document_status_service(kb_id: int, doc_id: int, status: str) -> dict:
    """更新文档状态（如：pending → indexed）"""
    db: Session = SessionLocal()
    try:
        doc = (
            db.query(Document)
            .filter(Document.id == doc_id, Document.knowledge_base_id == kb_id)
            .first()
        )
        if not doc:
            raise ValueError(f"文档不存在: {doc_id}")
        doc.status = status
        db.commit()
        db.refresh(doc)
        return {
            "id": doc.id,
            "status": doc.status,
            "updated_at": doc.created_at.isoformat() if doc.created_at else None,
        }
    finally:
        db.close()
