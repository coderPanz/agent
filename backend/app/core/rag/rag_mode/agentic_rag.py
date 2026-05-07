from dataclasses import dataclass
from typing import Optional
from langchain_core.documents import Document
from loguru import logger
from app.core.rag.rag_flow.rag_flow import (
    llm_route,
    relationship_score,
    generate_answer,
    recall_embeddings,
    build_index,
    check_index,
    rewrite_query,
)

# 1 次初始检索 + 最多 MAX_REWRITE 次改写重试
MAX_REWRITE = 2
SCORE_THRESHOLD = 0.65


@dataclass
class RagRound:
    retry_round: int
    query: str
    top_chunk: Optional[Document]
    relevance_score: float


def agentic_rag(query: str) -> str:
    if not check_index():
        logger.debug('向量索引不存在，重新构建')
        build_index()
        logger.info('构建索引成功')

    res = llm_route(query)
    if 'rag' not in res:
        return res

    return _rag_flow(query)


def _rag_flow(query: str) -> str:
    rounds: list[RagRound] = []
    current_query = query

    for round_num in range(MAX_REWRITE + 1):  # round 0=初始, 1~2=rewrite retry
        docs = recall_embeddings(current_query)

        if not docs:
            logger.debug(f'第 {round_num} 轮未召回文档，query={current_query!r}')
            rounds.append(RagRound(
                retry_round=round_num,
                query=current_query,
                top_chunk=None,
                relevance_score=0.0,
            ))
        else:
            score = relationship_score(current_query, docs)
            logger.debug(f'第 {round_num} 轮 score={score:.3f} query={current_query!r}')
            rounds.append(RagRound(
                retry_round=round_num,
                query=current_query,
                top_chunk=docs[0],
                relevance_score=score,
            ))

            if score >= SCORE_THRESHOLD:
                logger.info(f'第 {round_num} 轮相关性达标，直接生成答案')
                return generate_answer(current_query, docs, mode="agentic")

        if round_num < MAX_REWRITE:
            current_query = rewrite_query(query)
            logger.debug(f'第 {round_num + 1} 轮改写后 query={current_query!r}')

    # 全部轮次结束，选 score 最高的轮次
    best = max(rounds, key=lambda r: r.relevance_score)
    logger.info(f'最佳轮次: round={best.retry_round} score={best.relevance_score:.3f}')

    if best.top_chunk is None:
        return "当前知识库中未检索到任何相关内容，无法回答该问题，建议换个提问方式或扩充知识库。"

    return generate_answer(best.query, [best.top_chunk], mode="agentic")
