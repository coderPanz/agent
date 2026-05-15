"""Agent-HumanApproval: Human-in-the-loop 审批节点"""
from app.core.agent.state import AgentState


async def human_approval_node(state: AgentState) -> dict:
    """
    等待人工审批。图在此节点 interrupt，恢复时注入 human_approved=True/False。
    默认 None 表示尚未决策。
    """
    return {}
