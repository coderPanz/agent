"""Agent-MemoryWrite: 将本轮对话写入记忆"""
from app.core.agent.state import AgentState
from app.core.agent.memory.manager import MemoryManager


async def memory_write_node(state: AgentState) -> dict:
    """将本轮 user 消息和 final_answer 写入短期记忆。"""
    user_msg = ""
    for msg in reversed(state.messages):
        if msg.type == "human":
            user_msg = msg.content
            break

    if user_msg and state.final_answer:
        mgr = MemoryManager(session_id=state.session_id)
        await mgr.write_turn(user_msg, state.final_answer)

    return {}
