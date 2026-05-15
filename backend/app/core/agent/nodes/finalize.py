"""Agent-Finalize: 最终回答格式化"""
from langchain_core.messages import AIMessage
from app.core.agent.state import AgentState


async def finalize_node(state: AgentState) -> dict:
    """
    将 final_answer 写入 messages，确保对话历史完整。
    对于 chat 意图，final_answer 由 LLM 直接产生，需在此填充。
    """
    if state.final_answer:
        return {"messages": [AIMessage(content=state.final_answer)]}

    # chat 路径：取最后一条 AI 消息作为 final_answer
    for msg in reversed(state.messages):
        if msg.type == "ai":
            return {
                "final_answer": msg.content,
                "messages": [],
            }

    return {}
