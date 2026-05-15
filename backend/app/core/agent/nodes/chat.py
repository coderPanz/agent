"""Agent-Chat: 普通对话执行节点"""
from langchain_core.messages import AIMessage
from app.core.agent.state import AgentState
from app.services.llm import init_llm_client


async def chat_node(state: AgentState) -> dict:
    """直接调用 LLM 回复，不走工具。"""
    llm = init_llm_client()
    resp = await llm.ainvoke(state.messages)
    return {
        "final_answer": resp.content,
        "messages": [AIMessage(content=resp.content)],
    }
