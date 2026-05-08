"""RAG 服务"""
from app.core.rag.rag_mode.agentic_rag import agentic_rag
from app.core.rag.rag_mode.common_rag import common_rag


"""====================RAG 搜索====================="""
def rag_search(query: str, mode: str = "agentic") -> str:
    """RAG 搜索"""
    if mode == "agentic":
        return agentic_rag(query)
    elif mode == "common":
        return common_rag(query)
    else:
        raise ValueError(f"Invalid mode: {mode}")