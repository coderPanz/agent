# agent-服务
from app.core.agent.agent import agent_chat as agent_chat_service
def agent_chat(query: str):
    """Agent-对话"""
    return agent_chat_service(query)