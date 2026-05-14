"""Agent-CallbackHandler: LangChain 回调钩子"""
#  LangChain 异步回调处理器，专门用来监听、追踪、拦截、自定义处理 LangChain 运行时的事件（比如 LLM 开始调用、结束、报错、流式输出等）。

from langchain_core.callbacks import AsyncCallbackHandler
from app.core.agent.observability.logger import get_logger, log_json

class AgentCallbackHandler(AsyncCallbackHandler):
    """
    LangChain 回调钩子：自动捕获 LLM 调用和 Token 消耗。
    在 llm.ainvoke(..., config={"callbacks": [handler]}) 时生效。
    """
    def __init__(self, session_id: str):
        self._logger = get_logger(f"callback.{session_id}")
        self.session_id = session_id

    async def on_llm_start(self, serialized, prompts, **kwargs):
        log_json(self._logger, "llm_start", session=self.session_id)

    async def on_llm_end(self, response, **kwargs):
      # getattr 是 Python 内置函数，用来安全地读取对象属性。
        usage = getattr(response, "llm_output", {}).get("token_usage", {})
        log_json(self._logger, "llm_end",
                 session=self.session_id,
                 prompt_tokens=usage.get("prompt_tokens", 0),
                 completion_tokens=usage.get("completion_tokens", 0))

    async def on_tool_start(self, serialized, input_str, **kwargs):
        log_json(self._logger, "tool_start",
                 session=self.session_id, tool=serialized.get("name"))

    async def on_tool_end(self, output, **kwargs):
        log_json(self._logger, "tool_end",
                 session=self.session_id, output_len=len(str(output)))



