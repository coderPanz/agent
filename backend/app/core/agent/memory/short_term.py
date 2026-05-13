from typing import Any

# 简单的内存存储，生产环境替换为 Redis
_store: dict[str, list] = {}

class ShortTermMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        if session_id not in _store:
            _store[session_id] = []

    async def get_all(self) -> list[dict]:
        return _store[self.session_id]
    
    async def append(self, message: dict[str, Any]):
        _store[self.session_id].append(message)
    
    async def trim_if_needed(self, max_turns: int, summarizer):
        """超过 max_turns 轮时，把最早的一半压缩为摘要"""
        msgs = _store[self.session_id]
        if len(msgs) > max_turns * 2:
            old = msgs[:max_turns]
            summary = await summarizer.summarize(old)
            # 用摘要替换旧消息
            _store[self.session_id] = [
                {"role": "system", "content": f"[历史摘要] {summary}"}
            ] + msgs[max_turns:]