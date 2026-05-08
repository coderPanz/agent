# llm 服务
import os
from openai import OpenAI
from dotenv import load_dotenv
from loguru import logger
load_dotenv()
# 1. 模型 sdk 初始化
_llm_client = None

def init_llm_client():
    logger.info("初始化 llm 客户端")
    global _llm_client
    if not _llm_client:
        _llm_client = OpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
    return _llm_client