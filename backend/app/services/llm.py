# llm 服务
import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from loguru import logger
load_dotenv()

_llm_client = None

def init_llm_client():
    logger.info("初始化 llm 客户端")
    global _llm_client
    if not _llm_client:
        _llm_client = ChatOpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        )
    return _llm_client