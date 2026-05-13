"""Agent-Memory-Manager: 短期/长期/摘要 记忆管理"""
from app.core.agent.memory.short_term import ShortTermMemory
from app.core.agent.memory.summarizer import Summarizer


class MemoryManager:
    """
    统一记忆管理器，上层节点只与这个类交互。
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._short = ShortTermMemory(session_id)
        self._summarizer = Summarizer()

    async def get_summary(self) -> str:
        """获取历史摘要（如果短期记忆不够长，返回空字符串）"""
        history = await self._short.get_all()
        if len(history) < 10:
            return ""
        return await self._summarizer.summarize(history)
    
    async def write_turn(self, user_msg: str, assistant_msg: str):
        """写入一轮对话"""
        await self._short.append({"role": "user", "content": user_msg})
        await self._short.append({"role": "assistant", "content": assistant_msg})
        # 超过 20 条时自动压缩
        await self._short.trim_if_needed(max_turns=20, summarizer=self._summarizer)