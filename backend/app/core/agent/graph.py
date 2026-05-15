"""Agent-Graph: 编排状态机节点与条件路由"""
# StateGraph: LangGraph 的状态图对象
# 用于: 注册节点 定义边(edge) 构建工作流
# 类似: START -> router -> react -> finalize -> END
from langgraph.graph import StateGraph, START, END

# MemorySaver: LangGraph 内置的内存检查点存储器
# 作用: 保存 graph 执行状态-支持多轮对话-支持中断恢复-支持 human-in-the-loop
# 常用于: graph.compile(checkpointer=MemorySaver()) 这样 graph 每一步状态都会自动保存
from langgraph.checkpoint.memory import MemorySaver

from app.core.agent.state import AgentState
from app.core.agent.nodes.router import router_node
from app.core.agent.nodes.context_builder import context_builder_node
from app.core.agent.nodes.chat import chat_node
from app.core.agent.nodes.critic import critic_node
from app.core.agent.nodes.finalize import finalize_node
from app.core.agent.nodes.memory_write import memory_write_node
from app.core.agent.nodes.human_approval import human_approval_node
from app.core.agent.executors.react.executor import react_executor_node


def _route_after_router(state: AgentState) -> str:
    """Router 之后的路由函数：根据意图跳转到不同分支"""
    if state.intent in ("react", "rag"):
        return "context_builder"
    return "chat"   # 普通聊天走 chat_node

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
    builder.add_node("chat", chat_node)
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
        {"context_builder": "context_builder", "chat": "chat"},
    )

    # ── 固定边 ──
    builder.add_edge("chat", "finalize")
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
            lambda s: "memory_write" if s.human_approved else END, # 如果人工审批通过，则写入 memory，否则结束
            {"memory_write": "memory_write", END: END},
        )
    else:
        builder.add_edge("finalize", "memory_write")
    
    builder.add_edge("memory_write", END)

    return builder

def compile_graph(use_human_approval: bool = False, checkpointer=None):
    """编译图，返回可运行的 CompiledGraph"""
    builder = build_graph(use_human_approval)
    cp = checkpointer or MemorySaver()
    return builder.compile(checkpointer=cp)
