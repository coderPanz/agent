# 配置项目中各个模块需要的依赖
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# RAG 向量嵌入模型配置
EMBEDDING_MODEL_DIR = Path.home() / ".cache/modelscope/hub/models/BAAI/bge-large-zh-v1___5"
RERANKER_MODEL_DIR = Path.home() / ".cache/modelscope/hub/models/BAAI/bge-reranker-base"

# 召回分片数量 -rerank 数量
RECALL_TOP_K = 10
RERANK_TOP_K = 5

# 文本分片大小与重叠：影响索引粒度与上下文连贯性。
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# llm 配置
LLM_NAME = os.getenv("LLM_MODEL")
LLM_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")

# 数据文档路径
DOCS_PATH = Path(__file__).resolve().parents[2] / "data/docs"













