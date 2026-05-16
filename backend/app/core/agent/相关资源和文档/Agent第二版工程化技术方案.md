# Agent 第二版技术方案

> 基于第一版「图式状态机主控 + ReAct 子节点」的设计，渐进式升级为「可扩展、工程化、可维护」的 Agent 系统。  
> 面向 Python 初学者，每个模块配有详细中文注释的代码示例。

---

## 目录

1. [总体架构设计](#1-总体架构设计)
2. [推荐目录结构](#2-推荐目录结构)
3. [Agent State 设计](#3-agent-state-设计)
4. [Graph 设计](#4-graph-设计)
5. [Router 实现](#5-router-实现)
6. [Context Builder 实现](#6-context-builder-实现)
7. [ReAct Executor 实现](#7-react-executor-实现)
8. [Tool 系统实现](#8-tool-系统实现)
9. [Memory 实现](#9-memory-实现)
10. [Critic 实现](#10-critic-实现)
11. [Trace / Logging 实现](#11-trace--logging-实现)
12. [Agent Runtime 实现](#12-agent-runtime-实现)
13. [完整运行示例](#13-完整运行示例)
14. [后续扩展方向](#14-后续扩展方向)

---

## 1. 总体架构设计

### 1.1 系统全景图

```
用户请求
    │
    ▼
┌─────────────────────────────────────────────┐
│                Agent Runtime                │  ← 生命周期管理、异常兜底、流式输出
│  ┌─────────────────────────────────────┐   │
│  │          LangGraph 状态机            │   │
│  │                                     │   │
│  │  [Router] → [ContextBuilder]        │   │
│  │      ↓             ↓                │   │
│  │  [ReActExecutor] ←─┘                │   │
│  │      ↓ (循环: Thought→Action→Obs)   │   │
│  │  [SelfRefine?] → [Critic?]          │   │
│  │      ↓                              │   │
│  │  [Finalize] → [Memory&Trace写回]    │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
         │                    │
    Tool Registry         Memory Store
    (工具注册/调度)        (短期/长期记忆)
```

### 1.2 模块职责表


| 模块             | 文件                            | 职责                            |
| -------------- | ----------------------------- | ----------------------------- |
| Runtime        | `agent_runtime.py`            | 入口、流式输出、异常恢复、生命周期             |
| State          | `state.py`                    | 定义流经所有节点的数据结构                 |
| Graph          | `graph.py`                    | 编排状态机节点与条件路由                  |
| Router         | `nodes/router.py`             | 意图识别，决定走哪条分支                  |
| ContextBuilder | `nodes/context_builder.py`    | 组装 Prompt 上下文（记忆+对话+RAG+任务）   |
| ReActExecutor  | `executors/react/executor.py` | Thought→Action→Observation 循环 |
| ToolRegistry   | `tools/registry.py`           | 工具注册、权限、超时、重试                 |
| Memory         | `memory/manager.py`           | 短期/长期/摘要 记忆管理                 |
| Critic         | `nodes/critic.py`             | 结果质量检验，决定是否重试                 |
| Trace          | `observability/trace.py`      | 结构化日志、Token 统计、推理链记录          |


### 1.3 数据流（调用链）

```
请求进入 Runtime
    → 初始化 AgentState
    → Graph.invoke() 启动状态机
        → router_node()        # 分析意图
        → context_builder_node() # 组装上下文
        → react_executor_node()  # ReAct 循环（可多步）
            → tool_registry.execute()  # 调用工具
            → self_refine（可选）
        → critic_node()        # 质量校验（可选）
        → finalize_node()      # 组装最终回复
        → memory_write_node()  # 写回记忆
    → 流式/同步返回结果
```

### 1.4 生命周期

```
创建 Session → 初始化 State → 路由 → 执行 → 校验 → 写回 → 销毁 Session
                                ↑                    ↓
                            重试/修正 ←─────────── 失败/降级
```

---

## 2. 推荐目录结构

```
backend/app/core/agent/
│
├── agent_runtime.py          # Agent 入口：接收请求，启动图，管理流式输出
│
├── state.py                  # AgentState：所有节点共享的数据模型
│
├── graph.py                  # 主状态机：节点注册 + 条件路由编排
│
├── nodes/                    # 图中的每个节点
│   ├── __init__.py
│   ├── router.py             # 意图路由节点
│   ├── context_builder.py    # 上下文组装节点
│   ├── critic.py             # Critic 质量校验节点
│   ├── finalize.py           # 最终回复组装节点
│   ├── memory_write.py       # 记忆写回节点
│   └── human_approval.py     # 人机协作中断节点
│
├── executors/                # 可插拔执行单元
│   ├── base.py               # 执行单元抽象基类
│   └── react/
│       ├── executor.py       # ReAct 主循环
│       ├── prompts.py        # 提示词模板
│       ├── self_refine.py    # 自我修正模块
│       └── tool_processing.py # 工具输出后处理
│
├── tools/                    # 工具系统
│   ├── registry.py           # Tool 注册/调度/权限/超时/重试
│   ├── schemas.py            # Tool 输入输出 Schema
│   └── builtin/              # 内置工具
│       ├── search.py
│       └── calculator.py
│
├── memory/                   # 记忆系统
│   ├── manager.py            # 统一记忆管理器
│   ├── short_term.py         # 短期记忆（对话历史）
│   ├── long_term.py          # 长期记忆（持久化）
│   └── summarizer.py         # 摘要压缩
│
├── observability/            # 可观测性
│   ├── trace.py              # 结构化 Trace
│   ├── logger.py             # 日志封装
│   └── callback_handler.py   # LangChain Callback 钩子
│
└── config/
    └── settings.py           # Agent 配置（token budget、重试次数等）
```

---

## 3. Agent State 设计

### 3.1 核心思想

State 是所有节点共享的「信封」，节点只读取自己需要的字段，只写回自己负责的字段。

### 3.2 完整 State 代码

```python
# state.py
from __future__ import annotations
from typing import Annotated, Any, Literal
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
    elapsed_ms: int          # 耗时毫秒
    error: str | None = None


# ── ReAct 单步记录（用于 trace） ──────────────────────────
class ReActStep(BaseModel):
    step: int
    thought: str
    action: str | None = None
    observation: str | None = None


# ── Token 预算与使用统计 ──────────────────────────────────
class TokenUsage(BaseModel):
    budget: int = 4096        # 本次分配的最大 token 数
    used_prompt: int = 0
    used_completion: int = 0

    @property
    def remaining(self) -> int:
        return self.budget - self.used_prompt - self.used_completion


# ── 主 State ─────────────────────────────────────────────
class AgentState(BaseModel):
    # LangGraph 用 Annotated + add_messages 实现消息追加（不覆盖）
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
    critic_feedback: str = ""
    retry_count: int = 0
    max_retries: int = 2

    # ── 最终结果 ──
    final_answer: str = ""

    # ── Token 预算 ──
    token_usage: TokenUsage = Field(default_factory=TokenUsage)

    # ── 流程控制 ──
    error: str | None = None         # 节点抛出的错误信息
    human_approved: bool | None = None  # Human-in-the-loop 决策结果

    # ── 会话元信息 ──
    session_id: str = ""
    user_id: str = ""

    class Config:
        arbitrary_types_allowed = True  # 允许 BaseMessage 等非 Pydantic 类型
```

**关键点说明：**

- `messages` 用 `add_messages` 注解，每次节点返回新消息时自动追加而不是覆盖
- `react_steps` 记录完整推理链，方便 Trace
- `critic_passed` 用三值逻辑：`None`（未跑）/ `True`（通过）/ `False`（重试）
- `token_usage` 每个节点都可以往里累加，实现全局预算管控

---

## 4. Graph 设计

### 4.1 节点流转图

```
START
  │
  ▼
[router] ──→ intent = "react" ──→ [context_builder]
  │                                      │
  │ intent = "chat"                      ▼
  │                               [react_executor]
  │                                      │
  │                               critic_passed?
  │                               ├─ None/True ──→ [finalize]
  │                               └─ False ──────→ [react_executor] (重试，最多 max_retries 次)
  │                                                      │
  └──────────────────────────────────────────────────────┤
                                                         ▼
                                                  [memory_write]
                                                         │
                                                        END
```

### 4.2 Graph 代码

```python
# graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.core.agent.state import AgentState
from app.core.agent.nodes.router import router_node
from app.core.agent.nodes.context_builder import context_builder_node
from app.core.agent.nodes.critic import critic_node
from app.core.agent.nodes.finalize import finalize_node
from app.core.agent.nodes.memory_write import memory_write_node
from app.core.agent.nodes.human_approval import human_approval_node
from app.core.agent.executors.react.executor import react_executor_node


def _route_after_router(state: AgentState) -> str:
    """Router 之后的路由函数：根据意图跳转到不同分支"""
    if state.intent in ("react", "rag"):
        return "context_builder"
    return "finalize"   # 普通聊天直接结束


def _route_after_critic(state: AgentState) -> str:
    """Critic 之后的路由函数：通过→结束, 不通过且未超限→重试"""
    if state.critic_passed is False and state.retry_count < state.max_retries:
        return "react_executor"   # 重试
    return "finalize"


def build_graph(use_human_approval: bool = False) -> StateGraph:
    """
    构建主状态机图。
    use_human_approval=True 时在 finalize 前插入人工审批节点。
    """
    builder = StateGraph(AgentState)

    # ── 注册所有节点 ──
    builder.add_node("router", router_node)
    builder.add_node("context_builder", context_builder_node)
    builder.add_node("react_executor", react_executor_node)
    builder.add_node("critic", critic_node)
    builder.add_node("finalize", finalize_node)
    builder.add_node("memory_write", memory_write_node)

    if use_human_approval:
        builder.add_node("human_approval", human_approval_node)

    # ── 设置入口 ──
    builder.add_edge(START, "router")

    # ── 条件路由：Router 之后 ──
    builder.add_conditional_edges(
        "router",
        _route_after_router,
        {"context_builder": "context_builder", "finalize": "finalize"},
    )

    # ── 固定边 ──
    builder.add_edge("context_builder", "react_executor")
    builder.add_edge("react_executor", "critic")

    # ── 条件路由：Critic 之后（重试 or 结束）──
    builder.add_conditional_edges(
        "critic",
        _route_after_critic,
        {"react_executor": "react_executor", "finalize": "finalize"},
    )

    if use_human_approval:
        builder.add_edge("finalize", "human_approval")
        builder.add_conditional_edges(
            "human_approval",
            lambda s: "memory_write" if s.human_approved else END,
            {"memory_write": "memory_write", END: END},
        )
    else:
        builder.add_edge("finalize", "memory_write")

    builder.add_edge("memory_write", END)

    return builder


def compile_graph(checkpointer=None):
    """编译图，返回可运行的 CompiledGraph"""
    builder = build_graph()
    cp = checkpointer or MemorySaver()   # 默认使用内存 checkpointer
    return builder.compile(checkpointer=cp)
```

---

## 5. Router 实现

### 5.1 设计思路

Router 是流程的"交通指挥"：用最小代价（一次 LLM 调用或关键词匹配）判断用户意图，避免把所有请求都走昂贵的 ReAct 路径。

```python
# nodes/router.py
import json
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.agent.state import AgentState, IntentType
from app.services.llm import init_llm_client


# 意图识别的系统提示，要求模型只输出 JSON
ROUTER_SYSTEM_PROMPT = """
你是一个意图分类器。根据用户最后一条消息，返回 JSON：
{"intent": "<react|chat|rag|unknown>"}

- react : 需要调用工具、查询数据、执行操作
- chat  : 普通聊天、闲聊、无需工具
- rag   : 需要在知识库中检索文档
- unknown: 无法判断

只输出 JSON，不要任何解释。
"""


async def router_node(state: AgentState) -> dict:
    """
    意图路由节点。
    读取最后一条用户消息 → 调用 LLM 分类 → 写回 intent 字段。
    """
    # 取最后一条用户消息内容
    last_user_msg = ""
    for msg in reversed(state.messages):
        if msg.type == "human":
            last_user_msg = msg.content
            break

    # 调用 LLM 分类
    llm = init_llm_client()
    resp = await llm.ainvoke([
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=last_user_msg),
    ])

    # 解析 JSON，容错处理
    try:
        result = json.loads(resp.content)
        intent: IntentType = result.get("intent", "unknown")
    except Exception:
        intent = "unknown"

    return {"intent": intent}
```

**关键点：**

- 用 `ainvoke`（异步调用），配合整个图的 async 风格
- 只返回需要修改的字段 `{"intent": intent}`，不返回完整 state

---

## 6. Context Builder 实现

### 6.1 设计思路

ContextBuilder 负责把「记忆、对话历史、RAG 结果、任务状态」拼装成一段优质的 Prompt 上下文字符串，传递给后续的执行节点。它内置：

- 滑动窗口截断（保留最近 N 轮）
- Token 预算检查
- 优先级排序（系统信息 > 任务状态 > 记忆摘要 > 最近对话）

```python
# nodes/context_builder.py
from langchain_core.messages import BaseMessage
from app.core.agent.state import AgentState
from app.core.agent.memory.manager import MemoryManager


# Token 估算（粗略：1 个汉字约 1.5 token，英文 1 词约 1.3 token）
def _estimate_tokens(text: str) -> int:
    return int(len(text) * 1.5)


def _format_messages(messages: list[BaseMessage], max_turns: int = 10) -> str:
    """把最近 max_turns 轮对话格式化为字符串"""
    recent = messages[-max_turns * 2:]   # 一轮 = user + assistant 两条
    lines = []
    for msg in recent:
        role = "用户" if msg.type == "human" else "助手"
        lines.append(f"[{role}]: {msg.content}")
    return "\n".join(lines)


async def context_builder_node(state: AgentState) -> dict:
    """
    上下文组装节点：按优先级拼装所有上下文片段。
    写回 context_str 和 memory_summary 字段。
    """
    memory_mgr = MemoryManager(session_id=state.session_id)

    # ── 1. 获取记忆摘要 ──────────────────────────────────
    summary = await memory_mgr.get_summary()

    # ── 2. 格式化最近对话 ────────────────────────────────
    recent_dialogue = _format_messages(state.messages, max_turns=8)

    # ── 3. RAG 结果（本版先留空，后续接入） ───────────────
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
```

---

## 7. ReAct Executor 实现

### 7.1 设计思路

不使用 `create_react_agent`，而是**手动实现 Thought → Action → Observation 循环**，原因：

- 可以精确控制每一步的 Prompt
- 可以自定义工具失败恢复
- 可以在循环中记录每一步到 `react_steps`（用于 Trace）
- 可以做 hallucination 防护（检测模型是否捏造了不存在的工具）

### 7.2 Prompts

```python
# executors/react/prompts.py

REACT_SYSTEM_PROMPT = """
你是一个智能助手，按照 ReAct 格式逐步回答用户问题。

可用工具列表：
{tool_descriptions}

输出格式（严格遵守，每步只选一种）：

Thought: <你的分析推理>
Action: <工具名称>
Action Input: <JSON 格式的工具参数>

或者当得到答案时：

Thought: <最终分析>
Final Answer: <最终回复>

规则：
1. 每次只输出 Thought+Action 或 Thought+Final Answer，不能混用
2. Action Input 必须是合法 JSON
3. 如果工具返回错误，在 Thought 中分析原因，换一种方式重试
4. 最多执行 {max_steps} 步
"""

OBSERVATION_TEMPLATE = "Observation: {result}"
```

### 7.3 Executor 主循环

```python
# executors/react/executor.py
import json
import re
import time
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.agent.state import AgentState, ReActStep, ToolCallRecord
from app.core.agent.tools.registry import ToolRegistry
from app.core.agent.executors.react.prompts import REACT_SYSTEM_PROMPT, OBSERVATION_TEMPLATE
from app.core.agent.observability.trace import Tracer
from app.services.llm import init_llm_client


# 从 LLM 输出中解析 Action 和 Action Input
ACTION_RE = re.compile(r"Action:\s*(.+)")
ACTION_INPUT_RE = re.compile(r"Action Input:\s*(\{.+?\})", re.DOTALL)
FINAL_ANSWER_RE = re.compile(r"Final Answer:\s*(.+)", re.DOTALL)
THOUGHT_RE = re.compile(r"Thought:\s*(.+?)(?=\nAction|\nFinal Answer|$)", re.DOTALL)


def _parse_llm_output(text: str) -> dict:
    """
    解析 LLM 的 ReAct 格式输出。
    返回: {"thought": ..., "action": ..., "action_input": ..., "final_answer": ...}
    其中 action/action_input 或 final_answer 必有其一。
    """
    result = {}

    thought_match = THOUGHT_RE.search(text)
    result["thought"] = thought_match.group(1).strip() if thought_match else ""

    final_match = FINAL_ANSWER_RE.search(text)
    if final_match:
        result["final_answer"] = final_match.group(1).strip()
        return result

    action_match = ACTION_RE.search(text)
    input_match = ACTION_INPUT_RE.search(text)
    if action_match:
        result["action"] = action_match.group(1).strip()
        try:
            result["action_input"] = json.loads(input_match.group(1)) if input_match else {}
        except json.JSONDecodeError:
            result["action_input"] = {}

    return result


async def react_executor_node(state: AgentState) -> dict:
    """
    ReAct 执行节点：手动实现 Thought→Action→Observation 循环。
    """
    llm = init_llm_client()
    registry = ToolRegistry.get_instance()
    tracer = Tracer(session_id=state.session_id)

    # ── 构建工具描述文本，注入 Prompt ──────────────────────
    tool_desc = registry.get_descriptions()
    system_prompt = REACT_SYSTEM_PROMPT.format(
        tool_descriptions=tool_desc,
        max_steps=state.max_steps,
    )

    # ── 初始化对话历史（包含 ContextBuilder 组装的上下文） ──
    history = [
        SystemMessage(content=system_prompt),
        SystemMessage(content=f"上下文信息：\n{state.context_str}"),
    ] + list(state.messages)   # 追加完整对话历史

    # ── ReAct 主循环 ───────────────────────────────────────
    react_steps: list[ReActStep] = []
    tool_calls: list[ToolCallRecord] = []
    current_step = state.current_step

    for step_num in range(current_step, state.max_steps):
        await tracer.log_step_start(step_num)

        # 1. 调用 LLM 获取 Thought + Action/Final Answer
        llm_response = await llm.ainvoke(history)
        raw_text = llm_response.content

        # 2. 解析输出
        parsed = _parse_llm_output(raw_text)
        thought = parsed.get("thought", "")

        # 3. 如果是 Final Answer，退出循环
        if "final_answer" in parsed:
            react_steps.append(ReActStep(
                step=step_num,
                thought=thought,
                action=None,
                observation="[最终回答]",
            ))
            # 把最终回答追加到消息历史
            history.append(AIMessage(content=raw_text))
            await tracer.log_final_answer(parsed["final_answer"])
            return {
                "final_answer": parsed["final_answer"],
                "react_steps": react_steps,
                "tool_calls": tool_calls,
                "current_step": step_num + 1,
                "messages": [AIMessage(content=parsed["final_answer"])],
            }

        # 4. 没有 Action，防止死循环
        if "action" not in parsed:
            await tracer.log_error(step_num, "LLM 输出既无 Action 也无 Final Answer")
            break

        action_name = parsed["action"]
        action_input = parsed.get("action_input", {})

        # 5. 验证工具名（防止 hallucination：模型捏造不存在的工具）
        if not registry.has_tool(action_name):
            observation = f"错误：工具 '{action_name}' 不存在，可用工具：{registry.list_tool_names()}"

        else:
            # 6. 调用工具（带超时与重试）
            t0 = time.monotonic()
            tool_result = await registry.execute(action_name, action_input)
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            observation = tool_result.output
            tool_calls.append(ToolCallRecord(
                tool_name=action_name,
                input=action_input,
                output=observation,
                success=tool_result.success,
                elapsed_ms=elapsed_ms,
                error=tool_result.error,
            ))

        # 7. 记录本步
        react_steps.append(ReActStep(
            step=step_num,
            thought=thought,
            action=action_name,
            observation=observation,
        ))

        # 8. 把 Observation 追加到 history，进入下一步
        obs_text = OBSERVATION_TEMPLATE.format(result=observation)
        history.append(AIMessage(content=raw_text))
        history.append(HumanMessage(content=obs_text))

        await tracer.log_step_end(step_num, action_name, observation)

    # 超出最大步数，兜底回复
    fallback = "已达到最大推理步数，无法得出明确答案，请换一种方式提问。"
    return {
        "final_answer": fallback,
        "react_steps": react_steps,
        "tool_calls": tool_calls,
        "current_step": state.max_steps,
        "messages": [AIMessage(content=fallback)],
    }
```

### 7.4 Self-Refine 模块

```python
# executors/react/self_refine.py
from langchain_core.messages import HumanMessage
from app.services.llm import init_llm_client


REFINE_PROMPT = """
请审查以下回答是否准确、完整、逻辑清晰。

原始问题：{question}
当前回答：{answer}

如果回答已经足够好，请回复：PASS
如果有问题，请指出问题，然后给出改进后的完整回答，格式：
REVISE: <改进后的回答>
"""


async def self_refine(question: str, answer: str, max_rounds: int = 2) -> str:
    """
    自我修正：让 LLM 审查自己的输出，最多修正 max_rounds 次。
    返回最终（可能已修正的）回答。
    """
    llm = init_llm_client()
    current_answer = answer

    for _ in range(max_rounds):
        prompt = REFINE_PROMPT.format(question=question, answer=current_answer)
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        text = resp.content.strip()

        if text.startswith("PASS"):
            break   # 通过，不需要修改
        elif text.startswith("REVISE:"):
            current_answer = text[len("REVISE:"):].strip()
        else:
            break   # 格式异常，保留原答案

    return current_answer
```

---

## 8. Tool 系统实现

### 8.1 设计思路

ToolRegistry 是工具的统一入口：

- 注册：`@registry.register(name, permissions, timeout)`
- 调度：`registry.execute(name, input)` 内置超时 + 重试
- 校验：用 Pydantic Schema 验证入参，防止格式错误传给工具

### 8.2 Tool Schema 与结果

```python
# tools/schemas.py
from pydantic import BaseModel
from typing import Any


class ToolResult(BaseModel):
    """工具执行结果的标准格式"""
    tool_name: str
    output: str           # 工具输出（字符串化，方便放入 Prompt）
    success: bool
    error: str | None = None
    raw: Any = None       # 原始输出（可选保留）
```

### 8.3 Tool Registry

```python
# tools/registry.py
import asyncio
from typing import Callable, Any
from app.core.agent.tools.schemas import ToolResult


class ToolRegistry:
    """
    工具注册中心：管理所有可被 Agent 调用的工具。
    单例模式，全局唯一。
    """
    _instance: "ToolRegistry | None" = None

    def __init__(self):
        # {工具名: {"fn": 异步函数, "timeout": 秒, "max_retry": 次}}
        self._tools: dict[str, dict] = {}
        self._descriptions: dict[str, str] = {}   # 工具描述，注入 Prompt

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(
        self,
        name: str,
        description: str,
        timeout: float = 10.0,
        max_retry: int = 1,
    ):
        """装饰器：注册一个工具函数"""
        def decorator(fn: Callable):
            self._tools[name] = {"fn": fn, "timeout": timeout, "max_retry": max_retry}
            self._descriptions[name] = description
            return fn
        return decorator

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def list_tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def get_descriptions(self) -> str:
        """返回所有工具的描述文本，用于注入 Prompt"""
        lines = []
        for name, desc in self._descriptions.items():
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    async def execute(self, name: str, input_data: dict[str, Any]) -> ToolResult:
        """
        调用工具，内置超时控制和重试逻辑。
        """
        if name not in self._tools:
            return ToolResult(tool_name=name, output="", success=False, error=f"工具 {name} 未注册")

        meta = self._tools[name]
        fn = meta["fn"]
        timeout = meta["timeout"]
        max_retry = meta["max_retry"]

        last_error = ""
        for attempt in range(max_retry + 1):
            try:
                # asyncio.wait_for 实现超时控制
                raw = await asyncio.wait_for(fn(**input_data), timeout=timeout)
                return ToolResult(
                    tool_name=name,
                    output=str(raw)[:2000],   # 截断防止 token 爆炸
                    success=True,
                    raw=raw,
                )
            except asyncio.TimeoutError:
                last_error = f"工具 {name} 超时（{timeout}s）"
            except Exception as e:
                last_error = f"工具 {name} 执行错误：{e}"

        return ToolResult(tool_name=name, output="", success=False, error=last_error)
```

### 8.4 注册内置工具示例

```python
# tools/builtin/search.py
from app.core.agent.tools.registry import ToolRegistry

registry = ToolRegistry.get_instance()


@registry.register(
    name="web_search",
    description="搜索互联网信息。参数: {\"query\": \"搜索关键词\"}",
    timeout=15.0,
    max_retry=1,
)
async def web_search(query: str) -> str:
    """模拟网络搜索（实际接入搜索 API）"""
    # TODO: 接入真实搜索 API（如 Tavily、Serper）
    return f"[模拟搜索结果] 关于 '{query}' 的信息..."


@registry.register(
    name="calculator",
    description="数学计算。参数: {\"expression\": \"数学表达式，如 '2 + 3 * 4'\"}",
    timeout=5.0,
)
async def calculator(expression: str) -> str:
    """安全的数学表达式计算"""
    try:
        # 白名单字符，防止代码注入
        allowed = set("0123456789+-*/().% ")
        if not all(c in allowed for c in expression):
            return "错误：表达式包含非法字符"
        result = eval(expression)   # noqa: S307 (已做白名单过滤)
        return str(result)
    except Exception as e:
        return f"计算错误：{e}"
```

---

## 9. Memory 实现

### 9.1 三层记忆模型

```
短期记忆 (ShortTermMemory)
  └── 当前会话内的对话历史（in-memory，会话结束即清）

长期记忆 (LongTermMemory)
  └── 跨会话的用户偏好、关键信息（存 DB/Redis）

摘要记忆 (SummaryMemory)
  └── 当短期记忆超过阈值时，自动压缩为摘要
```

### 9.2 Memory Manager

```python
# memory/manager.py
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
```

### 9.3 Short Term Memory

```python
# memory/short_term.py
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
```

### 9.4 Summarizer

```python
# memory/summarizer.py
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
```

---

## 10. Critic 实现

### 10.1 设计思路

Critic 是独立的质量校验节点，评估 ReAct 的输出是否满足要求：

- 如果通过：流转到 finalize
- 如果不通过且未超重试上限：重回 react_executor（携带 feedback）
- 如果超重试上限：强制通过（兜底）

```python
# nodes/critic.py
import json
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.agent.state import AgentState
from app.services.llm import init_llm_client


CRITIC_PROMPT = """
你是一个严格的质量评估器。评估以下 AI 回答的质量。

用户问题：{question}
AI 回答：{answer}

评估标准：
1. 是否直接回答了用户问题？
2. 是否有明显的事实错误？
3. 是否足够完整？

只输出 JSON：
{{"pass": true/false, "feedback": "如果不通过，简述原因"}}
"""


async def critic_node(state: AgentState) -> dict:
    """
    Critic 校验节点：评估 final_answer 质量，决定是否重试。
    """
    # 超过重试上限，强制通过，避免无限循环
    if state.retry_count >= state.max_retries:
        return {"critic_passed": True, "critic_feedback": "已达重试上限，强制通过"}

    # 获取最后一条用户消息
    user_question = ""
    for msg in reversed(state.messages):
        if msg.type == "human":
            user_question = msg.content
            break

    llm = init_llm_client()
    prompt = CRITIC_PROMPT.format(question=user_question, answer=state.final_answer)
    resp = await llm.ainvoke([HumanMessage(content=prompt)])

    try:
        result = json.loads(resp.content)
        passed = result.get("pass", True)
        feedback = result.get("feedback", "")
    except Exception:
        passed = True   # 解析失败时默认通过
        feedback = ""

    new_retry = state.retry_count + (0 if passed else 1)

    return {
        "critic_passed": passed,
        "critic_feedback": feedback,
        "retry_count": new_retry,
    }
```

---

## 11. Trace / Logging 实现

### 11.1 Logger

```python
# observability/logger.py
import logging
import json
from datetime import datetime


def get_logger(name: str) -> logging.Logger:
    """返回带结构化格式的 Logger"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger


def log_json(logger: logging.Logger, event: str, **kwargs):
    """输出结构化 JSON 日志"""
    payload = {"event": event, "ts": datetime.utcnow().isoformat(), **kwargs}
    logger.info(json.dumps(payload, ensure_ascii=False))
```

### 11.2 Tracer

```python
# observability/trace.py
from app.core.agent.observability.logger import get_logger, log_json


class Tracer:
    """
    结构化 Trace 记录器：记录节点流转、工具调用、Token 消耗、推理链。
    每个 session 一个实例。
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._logger = get_logger(f"trace.{session_id}")

    async def log_step_start(self, step: int):
        log_json(self._logger, "react_step_start", session=self.session_id, step=step)

    async def log_step_end(self, step: int, action: str, observation: str):
        log_json(self._logger, "react_step_end",
                 session=self.session_id, step=step,
                 action=action, obs_len=len(observation))

    async def log_final_answer(self, answer: str):
        log_json(self._logger, "final_answer",
                 session=self.session_id, answer_len=len(answer))

    async def log_error(self, step: int, error: str):
        log_json(self._logger, "error",
                 session=self.session_id, step=step, error=error)

    async def log_token_usage(self, prompt_tokens: int, completion_tokens: int):
        log_json(self._logger, "token_usage",
                 session=self.session_id,
                 prompt=prompt_tokens, completion=completion_tokens)

    async def log_node(self, node_name: str, status: str, **kwargs):
        log_json(self._logger, "node_transition",
                 session=self.session_id, node=node_name, status=status, **kwargs)
```

### 11.3 Callback Handler（LangChain 钩子）

```python
# observability/callback_handler.py
from langchain_core.callbacks import AsyncCallbackHandler
from app.core.agent.observability.logger import get_logger, log_json


class AgentCallbackHandler(AsyncCallbackHandler):
    """
    LangChain 回调钩子：自动捕获 LLM 调用和 Token 消耗。
    在 llm.ainvoke(..., config={"callbacks": [handler]}) 时生效。
    """
    def __init__(self, session_id: str):
        self._logger = get_logger(f"callback.{session_id}")
        self.session_id = session_id

    async def on_llm_start(self, serialized, prompts, **kwargs):
        log_json(self._logger, "llm_start", session=self.session_id)

    async def on_llm_end(self, response, **kwargs):
        usage = getattr(response, "llm_output", {}).get("token_usage", {})
        log_json(self._logger, "llm_end",
                 session=self.session_id,
                 prompt_tokens=usage.get("prompt_tokens", 0),
                 completion_tokens=usage.get("completion_tokens", 0))

    async def on_tool_start(self, serialized, input_str, **kwargs):
        log_json(self._logger, "tool_start",
                 session=self.session_id, tool=serialized.get("name"))

    async def on_tool_end(self, output, **kwargs):
        log_json(self._logger, "tool_end",
                 session=self.session_id, output_len=len(str(output)))
```

---

## 12. Agent Runtime 实现

Runtime 是整个 Agent 的对外入口，负责：

1. 初始化 State
2. 启动图（同步 or 流式）
3. 全局异常捕获与降级
4. 流式输出封装

```python
# agent_runtime.py
import uuid
from typing import AsyncIterator
from langchain_core.messages import HumanMessage
from app.core.agent.state import AgentState, TokenUsage
from app.core.agent.graph import compile_graph
from app.core.agent.observability.trace import Tracer


class AgentRuntime:
    """
    Agent 运行时：对外暴露 chat() 和 stream_chat() 两个接口。
    """
    def __init__(self):
        self._graph = compile_graph()

    def _build_initial_state(self, query: str, session_id: str, user_id: str = "") -> AgentState:
        """构建初始 State"""
        return AgentState(
            messages=[HumanMessage(content=query)],
            session_id=session_id,
            user_id=user_id,
            token_usage=TokenUsage(budget=8192),
        )

    async def chat(self, query: str, session_id: str | None = None, user_id: str = "") -> str:
        """
        同步聊天接口：等待完整回复后返回字符串。
        """
        session_id = session_id or str(uuid.uuid4())
        tracer = Tracer(session_id=session_id)

        initial_state = self._build_initial_state(query, session_id, user_id)
        config = {"configurable": {"thread_id": session_id}}

        try:
            await tracer.log_node("runtime", "start", query_len=len(query))
            result = await self._graph.ainvoke(initial_state, config=config)
            await tracer.log_node("runtime", "end")
            return result["final_answer"] or result["messages"][-1].content
        except Exception as e:
            await tracer.log_error(-1, str(e))
            return f"抱歉，处理请求时遇到错误：{e}"

    async def stream_chat(
        self, query: str, session_id: str | None = None, user_id: str = ""
    ) -> AsyncIterator[str]:
        """
        流式聊天接口：逐步 yield token（适合 SSE / WebSocket 推送）。
        """
        session_id = session_id or str(uuid.uuid4())
        initial_state = self._build_initial_state(query, session_id, user_id)
        config = {"configurable": {"thread_id": session_id}}

        # LangGraph 的 astream 会在每个节点完成时 yield 状态快照
        async for chunk in self._graph.astream(initial_state, config=config, stream_mode="values"):
            # 只推送有最终回答的节点产物
            if chunk.get("final_answer"):
                yield chunk["final_answer"]
```

---

## 13. 完整运行示例

```python
# demo.py（放在项目根目录运行）
import asyncio
from app.core.agent.agent_runtime import AgentRuntime


async def main():
    runtime = AgentRuntime()

    # ── 示例 1：普通对话 ──────────────────────────────────
    print("=== 普通对话 ===")
    answer = await runtime.chat(
        query="你好，介绍一下你自己",
        session_id="demo-session-001",
    )
    print(f"回答：{answer}\n")

    # ── 示例 2：工具调用（需要 web_search 工具已注册） ────
    print("=== 工具调用 ===")
    answer = await runtime.chat(
        query="帮我搜索一下 Python LangGraph 的最新版本",
        session_id="demo-session-002",
    )
    print(f"回答：{answer}\n")

    # ── 示例 3：流式输出 ──────────────────────────────────
    print("=== 流式输出 ===")
    async for chunk in runtime.stream_chat(
        query="用工具计算 123 * 456",
        session_id="demo-session-003",
    ):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
```

**运行前准备：**

```bash
# 安装依赖
pip install langgraph langchain langchain-openai pydantic

# 设置环境变量
export OPENAI_API_KEY=sk-...
export LLM_MODEL=gpt-4o-mini
```

---

## 14. 后续扩展方向

### 14.1 Multi-Agent（多智能体）

在现有 Graph 中，把某个节点替换为「子 Agent 调用」：

```python
# 方案：每个子 Agent 也是一个 compile_graph()，通过 subgraph 嵌套
builder.add_node("research_agent", ResearchAgentRuntime().chat)
builder.add_node("code_agent", CodeAgentRuntime().chat)
```

关键设计原则：父 Agent 做任务分解（Planner），子 Agent 负责执行。

### 14.2 Planner（任务规划）

在 Router 之后、ReAct 之前加一个 Planner 节点：

```python
# 输入：用户目标
# 输出：分解后的子任务列表 → 存入 State.subtasks
# 后续：按顺序/并行执行每个子任务对应的执行单元
```

### 14.3 RAG 接入

在 ContextBuilder 中补全 RAG 分支：

```python
# nodes/context_builder.py
if state.intent == "rag":
    from app.core.rag.retriever import retrieve
    docs = await retrieve(query=user_query, top_k=5)
    state.rag_results = [d.page_content for d in docs]
```

RAG 模块与 Agent 模块完全解耦，只通过 `state.rag_results` 交换数据。

### 14.4 MCP Tool 接入

在 ToolRegistry 中新增 `register_mcp_tool` 方法：

```python
# tools/registry.py
def register_mcp_tool(self, mcp_client, tool_name: str):
    """把 MCP Server 暴露的工具注册为本地工具"""
    async def _wrapper(**kwargs):
        return await mcp_client.call_tool(tool_name, kwargs)
    self._tools[tool_name] = {"fn": _wrapper, "timeout": 30.0, "max_retry": 1}
```

### 14.5 Web Search 工具

替换 `tools/builtin/search.py` 中的模拟实现：

```python
# 接入 Tavily Search API
from tavily import TavilyClient

@registry.register(name="web_search", description="...", timeout=15.0)
async def web_search(query: str) -> str:
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    results = client.search(query, max_results=3)
    return "\n".join(r["content"] for r in results["results"])
```

### 14.6 Code Agent

新建 `executors/code/` 执行单元，专门处理代码生成、执行、调试任务：

```python
# 核心能力：
# 1. 生成代码（LLM）
# 2. 在沙箱中执行（Docker / subprocess）
# 3. 捕获执行结果 → 追加到 Observation
# 4. 迭代修正直到代码通过
```

---

## 附录：模块实现优先级（渐进式路线图）


| 阶段           | 模块                             | 说明           |
| ------------ | ------------------------------ | ------------ |
| **P0（立即实现）** | state.py                       | 所有模块的基础      |
| **P0**       | graph.py                       | 状态机骨架，串联所有节点 |
| **P0**       | nodes/router.py                | 入口，决定流程方向    |
| **P0**       | executors/react/executor.py    | 核心执行逻辑       |
| **P0**       | tools/registry.py              | 工具调度基础设施     |
| **P1（第二步）**  | nodes/context_builder.py       | 提升回复质量       |
| **P1**       | memory/manager.py              | 支持多轮对话       |
| **P1**       | observability/trace.py         | 可观测性         |
| **P2（第三步）**  | nodes/critic.py                | 质量保障         |
| **P2**       | executors/react/self_refine.py | 自我修正         |
| **P2**       | nodes/human_approval.py        | 人机协作         |
| **P3（扩展）**   | Multi-Agent / RAG / MCP        | 能力扩展         |


