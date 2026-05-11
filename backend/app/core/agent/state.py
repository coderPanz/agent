"""Agent-State: 定义流经所有节点的数据结构"""
"""
开启「延迟注解求值」
在没有这条语句时，Python 会立即执行类型注解：
- 写前向引用（类还没定义就用它做注解）会直接报错
- 复杂类型注解会拖慢代码加载速度
- 循环引用的类注解会卡死
不加 from __future__ import annotations 会报错！
class Node:
    # 这里用到了 Node，但类还没定义完
    def get_next(self) -> Node:
        return self.next
报错：NameError: name 'Node' is not defined
加上这行代码，Python 不会立刻计算注解，而是把注解存成字符串，等需要时再解析：
"""

from __future__ import annotations
# Literal是类型注解，表示字面量类型 Annotated: 给类型附加额外信息，不影响类型本身，但能给工具 / 框架用。
from typing import Annotated, Any, Literal
# pydantic: 数据验证库、用于数据验证、模型定义、序列化
# 定义数据结构（字段名 + 类型）、自动校验数据、自动把 JSON / 字典 转成 Python 对象、自动把对象转回 JSON
# 访问字段 print(user.name)
# 转字典 print(user.model_dump())
# 转 JSON print(user.model_dump_json())
# Field： 给字段加校验规则
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# ── 意图类型枚举 ──────────────────────────────────────────
IntentType = Literal["react", "chat", "rag", "unknown"]

# ── 工具调用记录 ──────────────────────────────────────────
class ToolCallRecord(BaseModel):
    tool_name: str
    input: dict[str, Any]
    output: str
    success: bool
    elapsed_ms: int # 耗时—毫秒
    error: str | None = None

# ── ReAct 单步记录（用于 trace） ──────────────────────────
class ReActStep(BaseModel):
    step: int
    thought: str
    action: str | None = None
    observation: str | None = None

# ── Token 预算与使用统计 ──────────────────────────────────
class TokenUsage(BaseModel):
    budget: int = 4096       # 本次分配的最大 token 数
    used_prompt: int = 0     # 已经发送给 LLM 的内容消耗的 token（输入）
    used_completion: int = 0 # LLM 返回的内容消耗的 token（输出）

    @property
    def remaining(self) -> int: # self 为当前实例
        return self.budget - self.used_prompt - self.used_completion
    
# ── 主 State ─────────────────────────────────────────────
"""
为什么不能用  rag_results: list[str] = [] ? 
导致 ：所有实例会共享同一个列表。
在 py 中：[] 、 {} 、 set() 等是引用类型，默认用 class 的 __dict__ 存储实例变量，在类定义阶段只创建了一次。
"""
class AgentState(BaseModel):
    # LangGraph 用 Annotated + add_messages 实现消息追加（不覆盖），add_messages 是给 LangGraph 用的，标记类型元信息，方便框架底层识别并处理
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)

    # ── 意图 ──
    intent: IntentType = "unknown"

    # ── 上下文（由 ContextBuilder 填充） ──
    context_str: str = ""          # 最终拼好的 Prompt 上下文字符串
    memory_summary: str = ""       # 历史摘要
    rag_results: list[str] = Field(default_factory=list)  # 预留 RAG 结果

    # ── ReAct 执行状态 ──
    react_steps: list[ReActStep] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    current_step: int = 0
    max_steps: int = 10

    # ── Critic ──
    critic_passed: bool | None = None   # None=未校验, True=通过, False=需重试
    critic_feedback: str = ""           # 校验反馈
    retry_count: int = 0
    max_retries: int = 2

    # ── 最终结果 ──
    final_answer: str = ""

    # ── Token 预算 ──
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    
    # —— 流程控制 ——
    error: str | None = None         # 节点抛出的错误信息
    human_approved: bool | None = None  # Human-in-the-loop 决策结果

    # —— 会话元信息 ——
    session_id: str = ""
    user_id: str = ""

    class Config:
        arbitrary_types_allowed = True  # 允许 BaseMessage 等非 Pydantic 类型