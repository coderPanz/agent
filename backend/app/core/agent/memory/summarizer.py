from langchain_core.messages import HumanMessage  
from app.services.llm import init_llm_client

class Summarizer:
    async def summarize(self, messages: list[dict]) -> str:
        """把一段对话历史压缩为摘要"""
        dialogue = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        prompt = f"请用 2-3 句话总结以下对话的关键信息：\n\n{dialogue}"
        llm = init_llm_client()
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        return resp.content