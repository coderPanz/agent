"""RAG 提示词管理器 — 从 prompt-map 目录按需加载 .md 文件"""
from pathlib import Path
from loguru import logger

_RAG_DIR = Path(__file__).parent / "prompt-map" / "rag"


def _load(filename: str) -> str:
    path = _RAG_DIR / filename
    if not path.exists():
        logger.warning(f"提示词文件不存在，返回空字符串: {path}")
        return ""
    return path.read_text(encoding="utf-8")


class RagPrompts:
    """RAG 各阶段提示词，首次访问时从磁盘读取并缓存。"""

    _cache: dict[str, str] = {}

    @classmethod
    def _get(cls, filename: str) -> str:
        if filename not in cls._cache:
            cls._cache[filename] = _load(filename)
        return cls._cache[filename]

    @property
    def llm_route(self) -> str:
        """智能路由：判断是否进入 RAG 流程"""
        return self._get("llm-route.md")

    @property
    def query_rewrite(self) -> str:
        """Query 改写：提升向量召回准确率"""
        return self._get("llm_query_rewrite.md")

    @property
    def generate_answer(self) -> str:
        """生成答案：基于召回文档给出结构化回答"""
        return self._get("llm_generate.md")

    @property
    def relationship_score(self) -> str:
        """相关性评分：对 query 与文档片段打 0~1 分"""
        return self._get("llm_relationship-score.md")


rag_prompts = RagPrompts()
