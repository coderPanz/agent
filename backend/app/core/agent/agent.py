# agent-core-engineer

from app.core.prompt.prompt_manage import AgentPrompts
from app.services.llm import llm_client
"""====================Agent-普通对话流程====================="""

def agent_chat(query: str):
    """Agent-普通对话"""
    system_prompt = AgentPrompts.agent_sys_prompt
    user_prompt = query
    response = llm_client.chat.completions.create(
        model=os.getenv("LLM_MODEL"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content