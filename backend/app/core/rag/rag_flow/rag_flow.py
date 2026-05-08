from pathlib import Path
from typing import List
from app.utils.config import DOCS_PATH
from loguru import logger
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.utils.config import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL_DIR, RERANKER_MODEL_DIR, RECALL_TOP_K, RERANK_TOP_K
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import chromadb
import torch
from app.services.llm import init_llm_client
from app.core.prompt.prompt_manage import rag_prompts
from dotenv import load_dotenv
import json
import os
import re
load_dotenv()
# chroma 客户端
_chroma_client = None
# BGE 向量化模型
_embedding_model = None


"""一、====================获取md文档====================="""
def load_docs():
    docs_path = Path(DOCS_PATH)
    if not docs_path.exists():
        raise FileNotFoundError(f"文档路径不存在: {docs_path}")
    # glob 遍历文件，递归匹配所有md文件
    loader = DirectoryLoader(
        path=str(docs_path),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()
    logger.debug(f"加载完成，共 {len(docs)} 篇文档")
    return docs



"""二、====================文档分片====================="""
def split_docs(
    documents: List[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> List[Document]:
    """
      Args:
        documents: 文档列表
        chunk_size: 分片大小
        chunk_overlap: 分片重叠
      Returns:
        chunks: 分片列表
    """
    size = chunk_size or CHUNK_SIZE
    overlap = chunk_overlap or CHUNK_OVERLAP
    logger.info("开始分片，chunk_size=%d overlap=%d", size, overlap)

    # langchain 递归字符串分块
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
    )
    chunks = splitter.split_documents(documents)
    logger.info("分片完成，共 %d 个 chunk", len(chunks))
    return chunks


"""====================加载 BGE 向量化模型====================="""
def embed_tool_init() -> bool:
    global _embedding_model
    model_dir = Path(EMBEDDING_MODEL_DIR)
    if not model_dir.exists():
        raise FileNotFoundError(f"模型目录不存在，请设置 BGE_MODEL_DIR：{model_dir}")
    if not any((model_dir / name).exists() for name in ("pytorch_model.bin", "model.safetensors")):
        raise FileNotFoundError(f"模型目录缺少权重文件：{model_dir}")
    if _embedding_model:
        return True

    # 加载分词器和模型
    _embedding_model = HuggingFaceBgeEmbeddings(
        model_name=str(model_dir),
        model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"},
        encode_kwargs={"normalize_embeddings": True},
        query_instruction="为这个句子生成表示以用于检索相关文章："
    )
    _embedding_model.query_instruction = "为这个句子生成表示以用于检索相关文章："
    logger.info("BGE 向量化模型已加载")
    return True


"""三、====================文档向量化====================="""
def embed_docs(texts: List[str]) -> List[torch.Tensor]:
    embed_tool_init()
    embeddings = torch.tensor(_embedding_model.embed_documents(texts))
    logger.debug(f"向量化完成，维度 = {embeddings.shape[1]}")
    return embeddings


"""====================初始化 chroma 客户端====================="""
def chroma_client_init() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client:
        return _chroma_client

    chroma_path = Path(DOCS_PATH).parent / "chroma"
    # PersistentClient 表示“持久化客户端”，数据会保存到磁盘；str(...) 是把 Path 对象转成字符串路径
    client = chromadb.PersistentClient(path=str(chroma_path))
    _chroma_client = client
    return client

"""四、====================向量化存储====================="""
def store_embeddings(chunks: List[Document], embeddings: torch.Tensor) -> None:
    # 向量化存储
    if len(chunks) != len(embeddings):
        raise ValueError(f"分片数量和向量数量不一致：chunks={len(chunks)} embeddings={len(embeddings)}")

    client_chroma = chroma_client_init()
    # collection 类似数据库中的一张表；不存在就创建，存在就直接拿来用
    collection = client_chroma.get_or_create_collection(name="rag_chunks")
    # 为每个分片生成一个唯一 id
    ids = [f"chunk-{index}" for index in range(len(chunks))]
    # 取出每个 Document 里的正文内容，作为 Chroma 要保存的文本
    documents = [chunk.page_content for chunk in chunks]
    # metadatas 保存每个分片的附加信息，例如来源文件路径、分片序号
    metadatas = [
        {
            **chunk.metadata,  # ** 表示把原来的 metadata 字典展开到这里
            "chunk_index": index,  # enumerate 会同时给出 index 和 chunk
        }
        for index, chunk in enumerate(chunks)
    ]
    # PyTorch Tensor 不能直接写入 Chroma；先脱离计算图，转到 CPU，再转成普通 Python list
    embedding_values = embeddings.detach().cpu().tolist()

    # upsert = update + insert：id 已存在就更新，不存在就插入
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embedding_values,
    )
    logger.info(f"向量已写入 Chroma，共 {len(chunks)} 个 chunk")

"""====================检查向量索引是否存在====================="""
def check_index() -> bool:
    client_chroma = chroma_client_init()
    collection = client_chroma.get_or_create_collection(name="rag_chunks")
    return collection.count() > 0

"""====================构建向量索引====================="""
def build_index() -> None:
    docs = load_docs()
    chunks = split_docs(docs)
    texts = [chunk.page_content for chunk in chunks]
    embeddings = embed_docs(texts)
    store_embeddings(chunks, embeddings)


"""五、====================向量召回 + rerank====================="""
def recall_embeddings(query: str, top_k: int = 10, rerank_top_k: int = 5) -> List[Document]:
    """向量召回"""
    if not query.strip():
        return []

    client_chroma = chroma_client_init()
    collection = client_chroma.get_or_create_collection(name="rag_chunks")

    # 用户问题向量化
    query_embedding = embed_docs([query])[0].detach().cpu().tolist()

    # 2. Chroma 返回最相似的 top_k 个分片；include 指定需要取回文本、元数据和距离
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    recalled_docs = [
        Document(
            page_content=document,
            metadata={
                **(metadata or {}),
                "distance": distance,
            },
        )
        for document, metadata, distance in zip(documents, metadatas, distances)
    ]
    if not recalled_docs:
        return []

    # 3. rerank：把“问题 + 分片文本”交给重排序模型打分，再按分数从高到低排序
    reranker_dir = Path(RERANKER_MODEL_DIR)
    if not reranker_dir.exists():
        logger.warning(f"rerank 模型目录不存在，跳过 rerank：{reranker_dir}")
        return recalled_docs[:rerank_top_k]

    tokenizer = AutoTokenizer.from_pretrained(reranker_dir)
    model = AutoModelForSequenceClassification.from_pretrained(reranker_dir)
    model.eval()

    pairs = [[query, doc.page_content] for doc in recalled_docs]
    encoded_input = tokenizer(pairs, padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        logits = model(**encoded_input).logits

    scores = logits[:, 1] if logits.ndim == 2 and logits.shape[1] > 1 else logits.squeeze(-1)
    ranked_docs = sorted(
        zip(scores.tolist(), recalled_docs),
        key=lambda item: item[0],
        reverse=True,
    )

    return [doc for _, doc in ranked_docs[:rerank_top_k]]


"""五b、====================向量召回 + rerank（含调试信息）====================="""
def recall_embeddings_debug(query: str, top_k: int = 10, rerank_top_k: int = 5) -> dict:
    """返回召回和 rerank 的详细调试信息"""
    import time

    if not query.strip():
        return {"docs": [], "candidates": [], "rerank_rows": [], "retrieve_ms": 0, "rerank_ms": 0}

    client_chroma = chroma_client_init()
    collection = client_chroma.get_or_create_collection(name="rag_chunks")

    t0 = time.time()
    query_embedding = embed_docs([query])[0].detach().cpu().tolist()
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    retrieve_ms = round((time.time() - t0) * 1000)

    documents = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    recalled_docs = [
        Document(
            page_content=doc,
            metadata={**(meta or {}), "distance": dist},
        )
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]

    candidates = [
        {
            "index": i,
            "source": str(metadatas[i].get("source", "unknown")) if metadatas[i] else "unknown",
            "preview": documents[i][:200],
        }
        for i in range(len(documents))
    ]

    if not recalled_docs:
        return {"docs": [], "candidates": candidates, "rerank_rows": [], "retrieve_ms": retrieve_ms, "rerank_ms": 0}

    t1 = time.time()
    reranker_dir = Path(RERANKER_MODEL_DIR)
    if not reranker_dir.exists():
        rerank_ms = 0
        final_docs = recalled_docs[:rerank_top_k]
        rerank_rows = [
            {"rank": i + 1, "score": 0.0, "original_index": i, "source": candidates[i]["source"], "preview": candidates[i]["preview"]}
            for i in range(min(rerank_top_k, len(recalled_docs)))
        ]
    else:
        tokenizer = AutoTokenizer.from_pretrained(reranker_dir)
        model = AutoModelForSequenceClassification.from_pretrained(reranker_dir)
        model.eval()
        pairs = [[query, doc.page_content] for doc in recalled_docs]
        encoded_input = tokenizer(pairs, padding=True, truncation=True, return_tensors='pt')
        with torch.no_grad():
            logits = model(**encoded_input).logits
        scores = logits[:, 1] if logits.ndim == 2 and logits.shape[1] > 1 else logits.squeeze(-1)
        ranked = sorted(enumerate(scores.tolist()), key=lambda x: x[1], reverse=True)
        rerank_ms = round((time.time() - t1) * 1000)

        final_docs = [recalled_docs[orig_i] for orig_i, _ in ranked[:rerank_top_k]]
        rerank_rows = [
            {
                "rank": rank + 1,
                "score": round(score, 4),
                "original_index": orig_i,
                "source": candidates[orig_i]["source"],
                "preview": candidates[orig_i]["preview"],
            }
            for rank, (orig_i, score) in enumerate(ranked[:rerank_top_k])
        ]

    return {
        "docs": final_docs,
        "candidates": candidates,
        "rerank_rows": rerank_rows,
        "retrieve_ms": retrieve_ms,
        "rerank_ms": rerank_ms,
    }


"""六、====================llm 生成答案====================="""
def generate_answer(query: str, docs: List[Document], mode: str = "common") -> str:
    """
    mode:
      "common"  — 通用对话，不注入文档
      "rag"     — 普通 RAG，注入召回文档作为上下文
      "agentic" — Agentic RAG，注入最佳轮次文档作为上下文
    """
    client = init_llm_client()

    if mode in ("rag", "agentic"):
        context = "\n\n---\n\n".join(doc.page_content for doc in docs)
        system_prompt = rag_prompts.generate_answer
        user_message = f"参考资料：\n{context}\n\n问题：{query}"
    else:
        system_prompt = "你是一个通用助手，请直接、准确地回答用户问题。"
        user_message = query

    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content

"""====================智能路由====================="""
def llm_route(query: str) -> str:
    client = init_llm_client()
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL"),
        messages=[
            {"role": "system", "content": rag_prompts.llm_route},
            {"role": "user", "content": query},
        ],
    )
    res = response.choices[0].message.content
    return "rag" if "rag" in res else res

"""====================重写 Query====================="""
def rewrite_query(query: str) -> str:
    client = init_llm_client()
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL"),
        messages=[
            {"role": "system", "content": rag_prompts.query_rewrite},
            {"role": "user", "content": query},
        ],
    )
    return response.choices[0].message.content.strip()


"""====================文本搜索关键字工具====================="""
def text_search_keyword(text: str):
  keywords = re.findall(r'\b\w+\b', text)
  return keywords

"""====================相关性评分====================="""
def relationship_score(query: str, docs: List[Document]) -> float:
    """使用 LLM 对 rerank 后的 top 文档评分，返回 0~1。"""
    if not query.strip() or not docs:
        return 0.0

    top_doc = docs[0]
    client = init_llm_client()
    try:
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL"),
            messages=[
                {"role": "system", "content": rag_prompts.relationship_score},
                {"role": "user", "content": f"用户问题：{query}\n\n文档片段：{top_doc.page_content}"},
            ],
        )
        raw = response.choices[0].message.content
        # 兼容 LLM 可能在 JSON 外包裹 markdown 代码块
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            score = float(data.get("score", 0.0))
            logger.debug(f"LLM 相关性评分: {score:.3f} | reason: {data.get('reason', '')}")
            return max(0.0, min(1.0, score))
    except Exception as e:
        logger.warning(f"LLM 相关性评分失败，回退字符级评分: {e}")

    # fallback：字符级重叠率
    query_chars = {c for c in query.lower() if c.strip()}
    if not query_chars:
        return 0.0
    content_chars = {c for c in top_doc.page_content.lower() if c.strip()}
    return len(query_chars & content_chars) / len(query_chars)


"""====================RAG 主函数====================="""
def rag_main(query: str, mode: str = "common") -> str:
    if mode == "common":
        logger.info("普通 RAG 模式")
        # 检查向量索引是否存在
        if not check_index():
            logger.warning("向量索引不存在，重新构建")
            build_index()
        # 向量召回
        docs = recall_embeddings(query, top_k=RECALL_TOP_K, rerank_top_k=RERANK_TOP_K)
        # llm 生成答案
        answer = generate_answer(query, docs, mode="rag")
        return answer
    elif mode == "agentic":
        # agentic rag mode flow
        """
        1. 智能路由
          1.1. 不需要查库
          1.2. 需要查库，则进行 rag 流程
        2. rag 流程
        3.  llm—rag 评分
          3.1 相关性不高，重新提示词+re-rag 流程
          3.2 相关性高，生成答案
          3.3 设置最大重复次数
        4. llm 生成返回答案
        """
        pass