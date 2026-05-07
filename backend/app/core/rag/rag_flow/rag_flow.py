from pathlib import Path
from typing import List
from app.utils.config import DOCS_PATH
from loguru import logger
from langchain_core.documents import Document
from app.utils.config import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL_DIR
from transformers import AutoModel, AutoTokenizer
import chromadb
import torch



"""一、====================获取md文档====================="""
def load_docs():
    docs_path = Path(DOCS_PATH)
    if not docs_path.exists():
        raise FileNotFoundError(f"文档路径不存在: {docs_path}")
    # glob 遍历文件，递归匹配所有md文件
    loader = DirectoryLoader(
        path=str(path),
        glob="**/*.md",
        loader_cls=UnstructuredMarkdownLoader,
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



"""三、====================文档向量化====================="""
def embed_docs(texts: List[str]) -> List[torch.Tensor]:
    """加载 BGE 向量化模型"""
    model_dir = Path(EMBEDDING_MODEL_DIR)
    if not model_dir.exists():
        raise FileNotFoundError(f"模型目录不存在，请设置 BGE_MODEL_DIR：{model_dir}")
    if not any((model_dir / name).exists() for name in ("pytorch_model.bin", "model.safetensors")):
        raise FileNotFoundError(f"模型目录缺少权重文件：{model_dir}")

    # 加载分词器和模型
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModel.from_pretrained(model_dir)
    model.eval()
    logger.info("BGE 向量化模型已加载")

    """向量化"""
    logger.debug(f"向量化 {len(texts)} 条文本...")
    encoded_input = tokenizer(texts, padding=True, truncation=True, return_tensors='pt')

    with torch.no_grad():
        model_output = model(**encoded_input)
        sentence_embeddings = model_output[0][:, 0]

    embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
    logger.debug(f"向量化完成，维度 = {embeddings.shape[1]}")
    return embeddings


"""四、====================向量化存储====================="""
def store_embeddings(chunks: List[Document], embeddings: torch.Tensor) -> None:
    # 向量化存储
    if len(chunks) != len(embeddings):
        raise ValueError(f"分片数量和向量数量不一致：chunks={len(chunks)} embeddings={len(embeddings)}")

    chroma_path = Path(DOCS_PATH).parent / "chroma"
    # PersistentClient 表示“持久化客户端”，数据会保存到磁盘；str(...) 是把 Path 对象转成字符串路径
    client = chromadb.PersistentClient(path=str(chroma_path))
    # collection 类似数据库中的一张表；不存在就创建，存在就直接拿来用
    collection = client.get_or_create_collection(name="rag_chunks")

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
    logger.info(f"向量已写入 Chroma：{chroma_path}，共 {len(chunks)} 个 chunk")