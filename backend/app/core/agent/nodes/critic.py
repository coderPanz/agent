"""Agent-Critic: 结果质量检验，决定是否重试"""
from app.core.agent.state import AgentState


async def critic_node(state: AgentState) -> dict:
    """
    校验 final_answer 质量。
    - 有内容且不是错误信息 → critic_passed=True
    - 空内容或明显错误 → critic_passed=False，触发重试
    """
    answer = state.final_answer.strip()
    retry_count = state.retry_count

    if not answer or answer.startswith("抱歉，处理请求时遇到错误"):
        return {
            "critic_passed": False,
            "critic_feedback": "回答为空或包含错误，需要重试",
            "retry_count": retry_count + 1,
        }

    return {"critic_passed": True, "critic_feedback": ""}
