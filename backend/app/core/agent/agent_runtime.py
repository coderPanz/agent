"""Agent-Runtime: 入口、流式输出、异常恢复、生命周期"""

import uuid
# 异步迭代器的标准类型
from typing import AsyncIterator
from langchain_core.messages import HumanMessage
from app.core.agent.state import AgentState, TokenUsage
from app.core.agent.graph import compile_graph
from app.core.agent.observability.trace import Tracer


class AgentRuntime:
    """
    Agent 运行时：对外暴露 chat() 和 stream_chat() 两个接口。
    """
    def __init__(self):
        self._graph = compile_graph()
    
    def _build_initial_state(self, query: str, session_id: str, user_id: str = "") -> AgentState:
        """构建初始 State"""
        return AgentState(
            messages = [HumanMessage(content=query)],
            session_id=session_id,
            user_id=user_id,
            token_usage=TokenUsage(budget=8192),
        )
    
    async def chat(self, query: str, session_id: str | None, user_id: str = "") -> str:
        """
        同步聊天接口：等待完整回复后返回字符串。
        """
        session_id = session_id or str(uuid.uuid4())
        tracer = Tracer(session_id=session_id)

        initial_state = self._build_initial_state(query, session_id, user_id)
        config = {"configurable": {"thread_id": session_id}}

        try:
            await tracer.log_node("runtime", "start", query_len=len(query))
            result = await self._graph.ainvoke(initial_state, config = config)
            await tracer.log_node("runtime", "end")
            return result["final_answer"] or result["messages"][-1].content
        except Exception as e:
            await tracer.log_error(-1, str(e))
            return f"抱歉，处理请求时遇到错误：{e}"


    async def stream_chat(self, query: str, session_id: str | None, user_id: str = "") -> AsyncIterator[str]:
        """
        流式聊天接口：逐步 yield token（适合 SSE / WebSocket 推送）。
        """
        session_id = session_id or str(uuid.uuid4())
        initial_state = self._build_initial_state(query, session_id, user_id)
        config = {"configurable": {"thread_id": session_id}}
        
        # LangGraph 的 astream 会在每个节点完成时 yield 状态快照
        # yield 暂停函数执行，返回当前值，等待下次调用继续执行
        yielded = False
        async for chunk in self._graph.astream(initial_state, config=config, stream_mode="values"):
            if not yielded and chunk.get("final_answer"):
                yield chunk["final_answer"]
                yielded = True






