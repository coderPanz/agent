"""
Agent-ContextBuilder: 组装上下文
ContextBuilder 负责把「记忆、对话历史、RAG 结果、任务状态」拼装成一段优质的 Prompt 上下文字符串，传递给后续的执行节点。它内置：
- 滑动窗口截断（保留最近 N 轮）
- Token 预算检查
- 优先级排序（系统信息 > 任务状态 > 记忆摘要 > 最近对话）
"""


"""
python 切片规则
lst[start : end : step]
start：开始下标（包含）
end：结束下标（不包含）
step：步长（隔几个取一个，默认 1）

缺省规则：
省略 start → 从开头开始
省略 end → 取到末尾结束
省略 step → 步长为 1，逐个取

"""
from langchain_core.messages import BaseMessage
from app.core.agent.state import AgentState
from app.core.agent.memory.manager import MemoryManager

# token 计算
def _estimate_tokens(text: str) -> int:
    return int(len(text) * 1.5)

def _format_message(message: list[BaseMessage], max_turns: int = 10) -> str:
    """把最近 max_turns 轮对话格式化为字符串"""
    # 倒数第 max_turns 条开始取到最后一条
    recent = message[-10 * 2:] # 一轮 = user + assistant 两条
    lines = []
    for msg in recent:
        role = "用户" if msg.type == "human" else "助手"
        lines.append(f'[{role}]: {msg.content}')
    # 把 列表里的每一段字符串，用 换行符 \n 连接起来。
    return '\n'.join(lines)

async def context_builder_node(state: AgentState) -> dict:
    """
    上下文组装节点：按优先级拼装所有上下文片段。
    写回 context_str 和 memory_summary 字段。
    """
    memory_mgr = MemoryManager(session_id = state.session_id)

    # ── 1. 获取记忆摘要 ──────────────────────────────────
    summary = await memory_mgr.get_summary()

    # ── 2. 格式化最近对话──────────────────────────────────
    recent_dialogue = _format_message(state.messages, max_turns=8)

    # ── 3. RAG【后续接入】 ──────────────────────────────────
    rag_text = "\n".join(state.rag_results) if state.rag_results else ""

    # ── 4. 按优先级组装，并做 Token 预算裁剪 ──────────────
    budget = state.token_usage.budget
    parts = []

    # 高优先级：任务目标（固定，不裁剪）
    parts.append("【当前任务】\n根据用户请求提供帮助。\n")

    # 中优先级：记忆摘要
    if summary and _estimate_tokens(summary) < budget * 0.2:
        parts.append(f"【历史摘要】\n{summary}\n")
    
    # 中优先级：RAG 检索结果
    if rag_text and _estimate_tokens(rag_text) < budget * 0.3:
        parts.append(f"【相关知识】\n{rag_text}\n")

    # 低优先级：最近对话（剩余 token 全给它）
    parts.append(f"【最近对话】\n{recent_dialogue}\n")
    context_str = "\n".join(parts)

    return {
      "context_str": context_str,
      "memory_summary": summary,
    }

