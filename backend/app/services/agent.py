# agent-服务
from app.core.agent.agent import agent_chat

"""====================Agent-对话服务====================="""
def agent_chat_service(query: str):
    """Agent-对话"""
    return agent_chat(query)