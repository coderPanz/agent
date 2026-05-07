# 普通 RAG 模式
from app.core.rag.rag_flow.rag_flow import (
    build_index,
    check_index,
    generate_answer,
    recall_embeddings,
)
from app.utils.config import RECALL_TOP_K, RERANK_TOP_K
from loguru import logger


def common_rag(query: str) -> str:
    # strip 去除首尾空格
    if not query.strip():
        return "请输入有效问题"

    # 检查向量索引是否存在，不存在则先构建
    if not check_index():
        logger.warning("向量索引不存在，开始构建")
        build_index()
        logger.info("向量索引构建完成")

    # 向量召回 + rerank
    docs = recall_embeddings(query, top_k=RECALL_TOP_K, rerank_top_k=RERANK_TOP_K)
    if not docs:
        return "没有召回到相关文档"

    # 基于召回文档生成答案
    return generate_answer(query, docs, mode="rag")